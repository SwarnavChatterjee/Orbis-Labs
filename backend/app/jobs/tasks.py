import asyncio
from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.collectors.registry import route_sources
from app.core.database import SessionFactory
from app.llm.parser import PlannerError, parse_query
from app.models.db import QueryRecord, utc_now
from app.models.schemas import QueryPlan


async def process_query(
    query_id: UUID,
    session_factory: async_sessionmaker[AsyncSession] = SessionFactory,
    parser: Callable[[str], QueryPlan] = parse_query,
) -> None:
    """Parse a queued query and persist its routed plan.

    This is intentionally isolated from collection. The durable Procrastinate
    worker can call this function later without changing the API contract.
    """

    async with session_factory() as session:
        query = await session.get(QueryRecord, query_id)
        if query is None:
            return

        query.status = "running"
        query.error_message = None
        query.updated_at = utc_now()
        await session.commit()

        try:
            plan = await asyncio.to_thread(parser, query.raw_text)
            routed_sources = route_sources(plan.intent, plan.filters.role)
            plan.sources = [source.id for source in routed_sources]
            query.parsed_params = plan.model_dump(mode="json")
            query.status = "planned"
            query.error_message = None
        except PlannerError as exc:
            query.status = "failed"
            query.error_message = str(exc)
        except Exception:
            # Provider/implementation details can contain request data or secrets.
            query.status = "failed"
            query.error_message = "The query planner could not complete the request. Please retry."
        finally:
            query.updated_at = utc_now()
            await session.commit()
