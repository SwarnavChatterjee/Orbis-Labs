import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select
from sqlmodel import SQLModel

from app.collectors.registry import CollectorRegistry
from app.jobs.tasks import process_query
from app.models.db import QueryEvent, QueryRecord, RecordRow
from app.models.schemas import QueryFilters, QueryPlan, Record, SourceDescriptor


engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False})
TestSessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_tables() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)


def test_process_query_persists_plan_and_routes_sources() -> None:
    async def scenario() -> None:
        await create_tables()
        query_id = uuid4()
        async with TestSessionFactory() as session:
            session.add(
                QueryRecord(
                    id=query_id,
                    raw_text="Find software engineering internships in India",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

        def fake_parser(_raw_text: str) -> QueryPlan:
            return QueryPlan(
                intent="internship_search",
                filters=QueryFilters(role="software_engineering"),
                sources=["model-invented-source"],
            )

        registry = CollectorRegistry()
        fixture_record = Record(
            company="Example Co",
            role="Software Intern",
            source_url="https://example.test/jobs/1",
            source_name="Fixture Source",
            retrieved_at=datetime.now(timezone.utc),
            confidence=0.9,
        )
        registry.register(
            SourceDescriptor(
                id="fixture_source",
                name="Fixture Source",
                kind="api",
                handles=["internship", "software_engineering"],
                collector="fixture.collect",
            ),
            lambda _plan, _source: [fixture_record],
        )
        await process_query(
            query_id,
            session_factory=TestSessionFactory,
            parser=fake_parser,
            collector_registry=registry,
        )
        await process_query(
            query_id,
            session_factory=TestSessionFactory,
            parser=fake_parser,
            collector_registry=registry,
        )

        async with TestSessionFactory() as session:
            query = await session.get(QueryRecord, query_id)
            assert query is not None
            assert query.status == "completed"
            assert query.parsed_params is not None
            assert query.parsed_params["sources"] == ["fixture_source"]
            records = (await session.scalars(
                select(RecordRow).where(RecordRow.query_id == query_id)
            )).all()
            assert len(records) == 1
            assert records[0].source_url == "https://example.test/jobs/1"
            statuses = (
                await session.scalars(
                    select(QueryEvent.status)
                    .where(QueryEvent.query_id == query_id)
                    .order_by(QueryEvent.id)
                )
            ).all()
            assert statuses == ["running", "planned", "collecting", "cleaning", "completed"]
        await engine.dispose()

    asyncio.run(scenario())


def test_process_query_persists_safe_failure() -> None:
    async def scenario() -> None:
        await create_tables()
        query_id = uuid4()
        async with TestSessionFactory() as session:
            session.add(QueryRecord(id=query_id, raw_text="some valid query"))
            await session.commit()

        def broken_parser(_raw_text: str) -> QueryPlan:
            raise RuntimeError("provider key=secret SQL details")

        await process_query(query_id, session_factory=TestSessionFactory, parser=broken_parser)
        async with TestSessionFactory() as session:
            query = await session.get(QueryRecord, query_id)
            assert query is not None
            assert query.status == "failed"
            assert query.error_message == (
                "The query planner could not complete the request. Please retry."
            )
        await engine.dispose()

    asyncio.run(scenario())


def test_process_query_sanitizes_unexpected_parser_error() -> None:
    async def scenario() -> None:
        await create_tables()
        query_id = uuid4()
        async with TestSessionFactory() as session:
            session.add(QueryRecord(id=query_id, raw_text="Find jobs"))
            await session.commit()

        def broken_parser(_raw_text: str) -> QueryPlan:
            raise RuntimeError("provider response contains secret-token")

        await process_query(query_id, session_factory=TestSessionFactory, parser=broken_parser)

        async with TestSessionFactory() as session:
            query = await session.get(QueryRecord, query_id)
            assert query is not None
            assert query.status == "failed"
            assert query.error_message == (
                "The query planner could not complete the request. Please retry."
            )
            assert "secret-token" not in query.error_message
        await engine.dispose()

    asyncio.run(scenario())
