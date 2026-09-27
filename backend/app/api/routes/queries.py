import asyncio
import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.collectors.registry import SOURCE_REGISTRY
from app.core.database import SessionFactory, get_session
from app.jobs.tasks import enqueue_query
from app.models.db import QueryEvent, QueryRecord, RecordRow, Source, utc_now
from app.models.schemas import ApiSuccess, QueryAccepted, QueryEventPayload, QueryStatus, QuerySubmission


router = APIRouter(prefix="/api", tags=["queries"])


def get_query_processor() -> Callable[[UUID], Awaitable[None]]:
    """Injection point retained for queue adapters and API tests."""

    return enqueue_query


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return SessionFactory


def not_found(message: str) -> HTTPException:
    return HTTPException(status_code=404, detail=message)


def _record_data(record: RecordRow, source_name: str | None) -> dict[str, object]:
    return {
        "id": record.id,
        "company": record.company,
        "role": record.role,
        "location": record.location,
        "stipend": record.stipend,
        "deadline": record.deadline,
        "source_url": record.source_url,
        "source_name": source_name,
        "retrieved_at": record.retrieved_at,
        "confidence": record.confidence,
        "validation_errors": record.validation_errors,
    }


@router.post("/queries", response_model=ApiSuccess, status_code=status.HTTP_202_ACCEPTED)
async def submit_query(
    payload: QuerySubmission,
    session: AsyncSession = Depends(get_session),
    query_processor: Callable[[UUID], Awaitable[None]] = Depends(get_query_processor),
) -> ApiSuccess:
    raw_text = payload.raw_text.strip()
    if len(raw_text) < 3:
        raise HTTPException(status_code=422, detail="raw_text must contain at least 3 non-space characters")
    query = QueryRecord(raw_text=raw_text)
    session.add(query)
    await session.flush()
    session.add(QueryEvent(query_id=query.id, status="queued"))
    await session.commit()
    await session.refresh(query)
    try:
        await query_processor(query.id)
    except Exception as exc:
        query.status = "failed"
        query.error_message = "Query could not be scheduled. Please try again."
        query.updated_at = utc_now()
        session.add(QueryEvent(query_id=query.id, status="failed", message=query.error_message))
        await session.commit()
        raise HTTPException(status_code=503, detail="Query could not be scheduled") from exc
    return ApiSuccess(data=QueryAccepted(query_id=query.id))


@router.get("/queries", response_model=ApiSuccess)
async def list_queries(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    query_status: QueryStatus | None = Query(default=None, alias="status"),
    session: AsyncSession = Depends(get_session),
) -> ApiSuccess:
    statement = select(QueryRecord)
    count_statement = select(func.count()).select_from(QueryRecord)
    if query_status:
        statement = statement.where(QueryRecord.status == query_status)
        count_statement = count_statement.where(QueryRecord.status == query_status)
    total = int((await session.scalar(count_statement)) or 0)
    result = await session.execute(
        statement.order_by(QueryRecord.created_at.desc(), QueryRecord.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [
        {
            "id": query.id,
            "raw_text": query.raw_text,
            "status": query.status,
            "error_message": query.error_message,
            "created_at": query.created_at,
            "updated_at": query.updated_at,
        }
        for query in result.scalars().all()
    ]
    return ApiSuccess(data={"items": items, "page": page, "page_size": page_size, "total": total})


@router.get("/queries/{query_id}", response_model=ApiSuccess)
async def get_query(
    query_id: UUID, session: AsyncSession = Depends(get_session)
) -> ApiSuccess:
    query = await session.get(QueryRecord, query_id)
    if query is None:
        raise not_found("Query was not found")
    count = int(
        (await session.scalar(select(func.count()).select_from(RecordRow).where(RecordRow.query_id == query_id)))
        or 0
    )
    return ApiSuccess(
        data={
            "id": query.id,
            "raw_text": query.raw_text,
            "status": query.status,
            "parsed_params": query.parsed_params,
            "error_message": query.error_message,
            "created_at": query.created_at,
            "updated_at": query.updated_at,
            "record_count": count,
        }
    )


@router.post("/queries/{query_id}/rerun", response_model=ApiSuccess, status_code=202)
async def rerun_query(
    query_id: UUID,
    session: AsyncSession = Depends(get_session),
    query_processor: Callable[[UUID], Awaitable[None]] = Depends(get_query_processor),
) -> ApiSuccess:
    previous = await session.get(QueryRecord, query_id)
    if previous is None:
        raise not_found("Query was not found")
    query = QueryRecord(raw_text=previous.raw_text, project_id=previous.project_id)
    session.add(query)
    await session.flush()
    session.add(QueryEvent(query_id=query.id, status="queued"))
    await session.commit()
    try:
        await query_processor(query.id)
    except Exception as exc:
        query.status = "failed"
        query.error_message = "Query could not be scheduled. Please try again."
        query.updated_at = utc_now()
        session.add(QueryEvent(query_id=query.id, status="failed", message=query.error_message))
        await session.commit()
        raise HTTPException(status_code=503, detail="Query could not be scheduled") from exc
    return ApiSuccess(data=QueryAccepted(query_id=query.id))


@router.get("/queries/{query_id}/results", response_model=ApiSuccess)
async def get_query_results(
    query_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    location: str | None = Query(default=None, max_length=200),
    role: str | None = Query(default=None, max_length=200),
    company: str | None = Query(default=None, max_length=200),
    min_confidence: float | None = Query(default=None, ge=0, le=1),
    session: AsyncSession = Depends(get_session),
) -> ApiSuccess:
    if await session.get(QueryRecord, query_id) is None:
        raise not_found("Query was not found")
    statement = select(RecordRow, Source.name).outerjoin(Source, RecordRow.source_id == Source.id).where(
        RecordRow.query_id == query_id
    )
    filters = []
    if location:
        filters.append(RecordRow.location.icontains(location, autoescape=True))
    if role:
        filters.append(RecordRow.role.icontains(role, autoescape=True))
    if company:
        filters.append(RecordRow.company.icontains(company, autoescape=True))
    if min_confidence is not None:
        filters.append(RecordRow.confidence >= min_confidence)
    if filters:
        statement = statement.where(*filters)
    total = int(
        (await session.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))) or 0
    )
    rows = await session.execute(
        statement.order_by(RecordRow.retrieved_at.desc(), RecordRow.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_record_data(record, source_name) for record, source_name in rows.all()]
    return ApiSuccess(data={"items": items, "page": page, "page_size": page_size, "total": total})


@router.get("/queries/{query_id}/sources", response_model=ApiSuccess)
async def get_query_sources(
    query_id: UUID, session: AsyncSession = Depends(get_session)
) -> ApiSuccess:
    if await session.get(QueryRecord, query_id) is None:
        raise not_found("Query was not found")
    result = await session.execute(
        select(Source.id, Source.name, Source.base_url, func.count(RecordRow.id).label("record_count"))
        .join(RecordRow, RecordRow.source_id == Source.id)
        .where(RecordRow.query_id == query_id)
        .group_by(Source.id, Source.name, Source.base_url)
        .order_by(Source.name)
    )
    return ApiSuccess(
        data=[
            {"id": str(row.id), "name": row.name, "base_url": row.base_url, "record_count": row.record_count}
            for row in result
        ]
    )


@router.get("/sources", response_model=ApiSuccess)
async def list_sources() -> ApiSuccess:
    return ApiSuccess(
        data=[
            {"id": source.id, "name": source.name, "kind": source.kind, "handles": source.handles}
            for source in SOURCE_REGISTRY.descriptors()
        ]
    )


async def stream_query_events(
    query_id: UUID,
    session_factory: async_sessionmaker[AsyncSession],
    after_id: int = 0,
    request: Request | None = None,
) -> AsyncGenerator[str, None]:
    cursor = after_id
    while True:
        if request is not None and await request.is_disconnected():
            return
        async with session_factory() as session:
            query = await session.get(QueryRecord, query_id)
            if query is None:
                return
            events = await session.scalars(
                select(QueryEvent)
                .where(QueryEvent.query_id == query_id, QueryEvent.id > cursor)
                .order_by(QueryEvent.id)
            )
            rows = events.all()
        for event in rows:
            payload = QueryEventPayload(
                query_id=query_id,
                status=event.status,
                timestamp=event.created_at,
                message=event.message,
            )
            cursor = event.id or cursor
            yield f"id: {cursor}\nevent: status\ndata: {payload.model_dump_json()}\n\n"
        if query.status in {"completed", "failed"}:
            return
        if not rows:
            yield ": keep-alive\n\n"
            await asyncio.sleep(1)


@router.get("/queries/{query_id}/stream")
async def stream_query(
    query_id: UUID,
    request: Request,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    session: AsyncSession = Depends(get_session),
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> StreamingResponse:
    if await session.get(QueryRecord, query_id) is None:
        raise not_found("Query was not found")
    try:
        after_id = max(0, int(last_event_id or 0))
    except ValueError:
        after_id = 0
    return StreamingResponse(
        stream_query_events(query_id, session_factory, after_id=after_id, request=request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
