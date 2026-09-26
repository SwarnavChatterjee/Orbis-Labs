import asyncio
from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.core.database import get_session
from app.api.routes.queries import get_query_processor
from app.main import app


engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False})
TestSessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_tables() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)


async def override_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionFactory() as session:
        yield session


async def no_op_processor(_query_id: UUID) -> None:
    return None


def test_query_submission_and_status() -> None:
    asyncio.run(create_tables())
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_query_processor] = lambda: no_op_processor
    try:
        with TestClient(app) as client:
            submitted = client.post(
                "/api/queries",
                json={"raw_text": "Find software engineering internships in India"},
            )
            assert submitted.status_code == 202
            body = submitted.json()
            assert body["success"] is True
            query_id = body["data"]["query_id"]
            UUID(query_id)

            fetched = client.get(f"/api/queries/{query_id}")
            assert fetched.status_code == 200
            assert fetched.json()["data"]["status"] == "queued"

            history = client.get("/api/queries")
            assert history.status_code == 200
            assert len(history.json()["data"]) == 1
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
