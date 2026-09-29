"""Shared collector filtering and record helpers."""

from __future__ import annotations

import re
from collections.abc import Iterable

from app.models.schemas import QueryPlan, Record


def compact(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def normalized(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def matches_plan(record: Record, plan: QueryPlan) -> bool:
    role = normalized(plan.filters.role)
    location = normalized(plan.filters.location)
    record_role = normalized(record.role)
    record_location = normalized(record.location)
    if role and role not in record_role and record_role not in role:
        return False
    if location and location not in record_location and record_location not in location:
        return False
    if plan.filters.remote is True and "remote" not in record_location:
        return False
    if plan.filters.remote is False and "remote" in record_location:
        return False
    return True


def limit_records(records: Iterable[Record], plan: QueryPlan) -> list[Record]:
    return [record for record in records if matches_plan(record, plan)][: plan.target_count]
