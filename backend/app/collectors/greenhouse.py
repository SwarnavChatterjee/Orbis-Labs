"""Greenhouse job-board collector.

GitLab's public Greenhouse board is the default API source for the MVP. The
parser accepts the public ``/v1/boards/{token}/jobs`` response shape and keeps
the HTTP boundary injectable for fixture tests.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.collectors.common import compact, limit_records
from app.models.schemas import QueryPlan, Record, SourceDescriptor


def parse_greenhouse_payload(
    payload: dict[str, Any], source: SourceDescriptor, retrieved_at: datetime | None = None
) -> list[Record]:
    retrieved = retrieved_at or datetime.now(timezone.utc)
    records: list[Record] = []
    for item in payload.get("jobs", []):
        url = item.get("absolute_url")
        title = compact(item.get("title"))
        location = compact((item.get("location") or {}).get("name"))
        if not url or not title:
            continue
        updated = item.get("updated_at")
        try:
            item_time = datetime.fromisoformat(updated.replace("Z", "+00:00")) if updated else retrieved
        except (AttributeError, ValueError):
            item_time = retrieved
        records.append(
            Record(
                company=source.name,
                role=title,
                location=location,
                source_url=url,
                source_name=source.name,
                retrieved_at=item_time,
                confidence=0.9,
            )
        )
    return records


def collect_greenhouse(
    plan: QueryPlan, source: SourceDescriptor, client: httpx.Client | None = None
) -> list[Record]:
    owns_client = client is None
    http_client = client or httpx.Client(timeout=20, follow_redirects=True)
    try:
        token = source.config["board_token"]
        response = http_client.get(source.config["jobs_url"].format(token=token))
        response.raise_for_status()
        return limit_records(parse_greenhouse_payload(response.json(), source), plan)
    finally:
        if owns_client:
            http_client.close()
