import asyncio
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.api.routes.queries import stream_query_events
from app.models.db import QueryEvent, QueryRecord


def test_stream_replays_persisted_events_and_closes_on_terminal_status() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        query_id = uuid4()
        async with factory() as session:
            session.add(QueryRecord(id=query_id, raw_text="some valid query", status="completed"))
            session.add_all(
                [
                    QueryEvent(query_id=query_id, status="queued"),
                    QueryEvent(query_id=query_id, status="completed"),
                ]
            )
            await session.commit()

        chunks = [chunk async for chunk in stream_query_events(query_id, factory)]
        assert len(chunks) == 2
        assert '"status":"queued"' in chunks[0]
        assert '"status":"completed"' in chunks[1]
        assert chunks[0].startswith("id: 1\nevent: status\n")
        await engine.dispose()

    asyncio.run(scenario())
