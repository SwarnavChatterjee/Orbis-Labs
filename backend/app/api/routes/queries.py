from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.jobs.tasks import process_query
from app.models.db import QueryRecord, RecordRow
from app.models.schemas import (
    ApiError,
    ApiSuccess,
    QueryAccepted,
    QuerySubmission,
)


router = APIRouter(prefix="/api/queries", tags=["queries"])


def get_query_processor():
    return process_query


def not_found(query_id: UUID) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=ApiError(error=f"Query {query_id} was not found").model_dump(),
    )


@router.post("", response_model=ApiSuccess, status_code=status.HTTP_202_ACCEPTED)
async def submit_query(
    payload: QuerySubmission,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    query_processor=Depends(get_query_processor),
) -> ApiSuccess:
    query = QueryRecord(raw_text=payload.raw_text.strip())
    session.add(query)
    await session.commit()
    await session.refresh(query)
    background_tasks.add_task(query_processor, query.id)
    return ApiSuccess(data=QueryAccepted(query_id=query.id))


@router.get("", response_model=ApiSuccess)
async def list_queries(
    session: AsyncSession = Depends(get_session),
) -> ApiSuccess:
    result = await session.execute(select(QueryRecord).order_by(QueryRecord.created_at.desc()))
    queries = result.scalars().all()
    return ApiSuccess(
        data=[
            {
                "id": query.id,
                "raw_text": query.raw_text,
                "status": query.status,
                "error_message": query.error_message,
                "created_at": query.created_at,
            }
            for query in queries
        ]
    )


@router.get("/{query_id}", response_model=ApiSuccess)
async def get_query(
    query_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ApiSuccess:
    query = await session.get(QueryRecord, query_id)
    if query is None:
        raise not_found(query_id)
    return ApiSuccess(
        data={
            "id": query.id,
            "raw_text": query.raw_text,
            "status": query.status,
            "parsed_params": query.parsed_params,
            "created_at": query.created_at,
            "updated_at": query.updated_at,
            "error_message": query.error_message,
        }
    )


@router.get("/{query_id}/results", response_model=ApiSuccess)
async def get_query_results(
    query_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ApiSuccess:
    if await session.get(QueryRecord, query_id) is None:
        raise not_found(query_id)
    result = await session.execute(
        select(RecordRow).where(RecordRow.query_id == query_id).order_by(RecordRow.retrieved_at.desc())
    )
    return ApiSuccess(data=result.scalars().all())


async def stream_query_events(query_id: UUID) -> AsyncGenerator[str, None]:
    """Placeholder for the SSE worker stream; implemented with the job runner."""

    yield f"event: status\ndata: {{\"query_id\": \"{query_id}\", \"status\": \"queued\"}}\n\n"
