import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.collectors.registry import SOURCE_REGISTRY
from app.jobs.tasks import process_query
from app.models.db import QueryRecord
from app.models.schemas import QueryFilters, QueryPlan


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
            )

        await process_query(query_id, session_factory=TestSessionFactory, parser=fake_parser)

        async with TestSessionFactory() as session:
            query = await session.get(QueryRecord, query_id)
            assert query is not None
            assert query.status == "planned"
            assert query.parsed_params is not None
            assert set(query.parsed_params["sources"]) == {
                source.id for source in SOURCE_REGISTRY
            }
        await engine.dispose()

    asyncio.run(scenario())
