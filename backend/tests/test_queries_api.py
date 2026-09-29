import asyncio
from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.core.database import get_session
from app.api.routes.queries import get_query_processor, get_session_factory
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


async def failing_processor(_query_id: UUID) -> None:
    raise RuntimeError("secret provider response")


def test_query_submission_and_status() -> None:
    asyncio.run(create_tables())
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_session_factory] = lambda: TestSessionFactory
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
            assert history.json()["data"]["total"] == 1
            assert len(history.json()["data"]["items"]) == 1

            results = client.get(f"/api/queries/{query_id}/results?page=1&page_size=10")
            assert results.status_code == 200
            assert results.json()["data"] == {
                "items": [], "page": 1, "page_size": 10, "total": 0
            }
            assert client.get(f"/api/queries/{query_id}/sources").json()["data"] == []
            assert client.get("/api/queries?page_size=1000").status_code == 422

            rerun = client.post(f"/api/queries/{query_id}/rerun")
            assert rerun.status_code == 202
            rerun_id = rerun.json()["data"]["query_id"]
            assert rerun_id != query_id
            assert client.get(f"/api/queries/{query_id}").json()["data"]["status"] == "queued"
            sources = client.get("/api/sources").json()
            assert sources["success"] is True
            assert [source["id"] for source in sources["data"]] == [
                "internshala",
                "gitlab_greenhouse",
            ]

            missing = client.get(f"/api/queries/{UUID(int=0)}")
            assert missing.status_code == 404
            assert missing.json() == {"success": False, "error": "Query was not found"}

            app.dependency_overrides[get_query_processor] = lambda: failing_processor
            failed = client.post(
                "/api/queries", json={"raw_text": "Find internships with safe queue testing"}
            )
            assert failed.status_code == 503
            assert failed.json() == {"success": False, "error": "Query could not be scheduled"}
            app.dependency_overrides[get_query_processor] = lambda: no_op_processor

            invalid = client.post("/api/queries", json={"raw_text": " "})
            assert invalid.status_code == 422
            assert invalid.json()["success"] is False

    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
