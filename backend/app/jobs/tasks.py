"""Query orchestration and the PostgreSQL-backed Procrastinate worker."""

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable
from typing import Any, Protocol
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.collectors.registry import SOURCE_REGISTRY, CollectorRegistry
from app.core.database import SessionFactory
from app.core.config import settings
from app.models.db import QueryEvent, QueryRecord, RecordRow, Source, utc_now
from app.llm.parser import PlannerError, PlannerTransportError
from app.models.schemas import QueryPlan

logger = logging.getLogger(__name__)

try:
    import procrastinate
except ImportError:  # Keeps SQLite unit tests independent of the worker package.
    procrastinate = None


class QueryPlanner(Protocol):
    """Planner boundary implemented by the OpenAI adapter or a test fake."""

    def parse(self, raw_text: str) -> QueryPlan | Awaitable[QueryPlan]: ...


class OpenAIQueryPlanner:
    """Default planner adapter; prompt and provider logic stay in the parser."""

    def parse(self, raw_text: str) -> QueryPlan:
        from app.llm.parser import parse_query

        return parse_query(raw_text)


def _worker_app() -> Any:
    if procrastinate is None:
        return None

    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    return procrastinate.App(
        connector=procrastinate.PsycopgConnector(conninfo=dsn),
        import_paths=["app.jobs.tasks"],
    )


procrastinate_app = _worker_app()


async def _record_transition(
    session: AsyncSession, query: QueryRecord, status: str, message: str | None = None
) -> None:
    query.status = status
    query.updated_at = utc_now()
    query.error_message = message if status == "failed" else None
    session.add(QueryEvent(query_id=query.id, status=status, message=message))
    await session.commit()


async def process_query(
    query_id: UUID,
    session_factory: async_sessionmaker[AsyncSession] = SessionFactory,
    parser: QueryPlanner | Callable[[str], QueryPlan | Awaitable[QueryPlan]] | None = None,
    collector_registry: CollectorRegistry = SOURCE_REGISTRY,
    worker_retry: bool = False,
    final_attempt: bool = True,
) -> None:
    """Parse, route, collect through registered adapters, and persist outcomes.

    Planner/collector calls run outside database transactions. A repeated job
    for a terminal query is a no-op, making worker retries idempotent.
    """

    async with session_factory() as session:
        query = await session.get(QueryRecord, query_id)
        if query is None or query.status == "completed":
            return
        if query.status == "failed" and not worker_retry:
            return
        raw_text = query.raw_text
        await _record_transition(session, query, "running")

    try:
        try:
            planner = parser or OpenAIQueryPlanner()
            parse = planner.parse if hasattr(planner, "parse") else planner
            if inspect.iscoroutinefunction(parse):
                plan = await parse(raw_text)
            else:
                plan = await asyncio.to_thread(parse, raw_text)
            if inspect.isawaitable(plan):
                plan = await plan
            if not isinstance(plan, QueryPlan):
                plan = QueryPlan.model_validate(plan)
        except PlannerError:
            raise
        except Exception as exc:
            raise PlannerTransportError(
                "The query planner could not complete the request. Please retry."
            ) from exc

        descriptors = collector_registry.route(plan.intent, plan.filters.role)
        plan.sources = [source.id for source in descriptors]
        async with session_factory() as session:
            query = await session.get(QueryRecord, query_id)
            if query is None:
                return
            query.parsed_params = plan.model_dump(mode="json")
            await _record_transition(session, query, "planned")

        collected: list[tuple[Any, Any]] = []
        if descriptors:
            async with session_factory() as session:
                query = await session.get(QueryRecord, query_id)
                if query is None:
                    return
                await _record_transition(session, query, "collecting")

            for descriptor in descriptors:
                registered = collector_registry.get(descriptor.id)
                if registered is None:
                    continue
                _, collector = registered
                if inspect.iscoroutinefunction(collector):
                    records = await collector(plan, descriptor)
                else:
                    records = await asyncio.to_thread(collector, plan, descriptor)
                if inspect.isawaitable(records):
                    records = await records
                collected.extend((descriptor, record) for record in records)

            async with session_factory() as session:
                query = await session.get(QueryRecord, query_id)
                if query is None:
                    return
                await _record_transition(session, query, "cleaning")
                for descriptor, record in collected:
                    parsed_url = urlsplit(str(record.source_url))
                    base_url = descriptor.config.get("base_url") or (
                        f"{parsed_url.scheme}://{parsed_url.netloc}"
                    )
                    source = await session.scalar(
                        select(Source).where(
                            Source.name == descriptor.name,
                            Source.base_url == base_url,
                        )
                    )
                    if source is None:
                        source = Source(
                            name=descriptor.name,
                            base_url=base_url,
                        )
                        session.add(source)
                        await session.flush()
                    existing = await session.scalar(
                        select(RecordRow.id).where(
                            RecordRow.query_id == query_id,
                            RecordRow.source_id == source.id,
                            RecordRow.source_url == str(record.source_url),
                        )
                    )
                    if existing is not None:
                        continue
                    session.add(
                        RecordRow(
                            query_id=query_id,
                            source_id=source.id,
                            company=record.company,
                            role=record.role,
                            location=record.location,
                            stipend=(record.stipend.model_dump(mode="json") if record.stipend else None),
                            deadline=record.deadline,
                            source_url=str(record.source_url),
                            retrieved_at=record.retrieved_at,
                            confidence=record.confidence,
                            validation_errors=record.validation_errors,
                        )
                    )
                await session.commit()

        async with session_factory() as session:
            query = await session.get(QueryRecord, query_id)
            if query is not None:
                message = "No registered collectors matched this query." if not descriptors else None
                await _record_transition(session, query, "completed", message)
    except PlannerError as exc:
        logger.error(
            "Query planning failed (%s)",
            type(exc).__name__,
            extra={"query_id": str(query_id)},
        )
        async with session_factory() as session:
            query = await session.get(QueryRecord, query_id)
            if query is not None and query.status != "completed":
                await _record_transition(session, query, "failed", str(exc))
        if worker_retry:
            raise
    except Exception as exc:
        logger.error(
            "Query processing failed (%s)",
            type(exc).__name__,
            extra={"query_id": str(query_id)},
        )
        async with session_factory() as session:
            query = await session.get(QueryRecord, query_id)
            if query is not None and query.status != "completed":
                # Keep provider, SQL, and collector details out of API responses.
                if worker_retry and not final_attempt:
                    await _record_transition(
                        session, query, "running", "A temporary processing error occurred; retrying."
                    )
                else:
                    await _record_transition(
                        session, query, "failed", "Query processing failed. Please try again."
                    )
        if worker_retry:
            raise


if procrastinate_app is not None:
    @procrastinate_app.task(
        name="app.jobs.tasks.process_query_job",
        retry=procrastinate.RetryStrategy(max_attempts=3),
        queue="queries",
        pass_context=True,
    )
    async def process_query_job(context: Any, query_id: str) -> None:
        await process_query(
            UUID(query_id), worker_retry=True, final_attempt=context.job.attempts >= 3
        )
else:
    process_query_job = None


async def enqueue_query(query_id: UUID) -> None:
    if process_query_job is None:
        raise RuntimeError("Procrastinate is not installed; durable queue is unavailable")
    await process_query_job.defer_async(query_id=str(query_id))


async def run_worker() -> None:
    if procrastinate_app is None:
        raise RuntimeError("Install the backend requirements to run the query worker")
    await procrastinate_app.run_worker_async(queues=["queries"], wait=True)


if __name__ == "__main__":
    asyncio.run(run_worker())
