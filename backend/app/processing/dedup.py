"""Deterministic duplicate grouping for source-backed records."""

from __future__ import annotations

from app.collectors.common import normalized
from app.models.schemas import Record


def deduplication_key(record: Record) -> tuple[str, str, str]:
    return normalized(record.company), normalized(record.role), normalized(record.location)


def deduplicate_records(records: list[Record]) -> list[Record]:
    selected: dict[tuple[str, str, str], Record] = {}
    for record in records:
        key = deduplication_key(record)
        current = selected.get(key)
        if current is None or record.confidence > current.confidence:
            selected[key] = record
        elif current is not None:
            merged_errors = sorted(set(current.validation_errors + record.validation_errors))
            selected[key] = current.model_copy(update={"validation_errors": merged_errors})
    return list(selected.values())
