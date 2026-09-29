"""Deterministic normalization and validation for collected records."""

from __future__ import annotations

import re

from app.models.schemas import Record


LOCATION_ALIASES = {
    "bengaluru": "Bangalore",
    "bombay": "Mumbai",
    "new delhi": "Delhi",
    "remote / work from home": "Remote",
}


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def clean_record(record: Record) -> Record:
    location = normalize_text(record.location) if record.location else None
    if location:
        location = LOCATION_ALIASES.get(location.lower(), location)
    errors = list(record.validation_errors)
    if not record.source_url:
        errors.append("missing_source_url")
    if not record.company:
        errors.append("missing_company")
    if not record.role:
        errors.append("missing_role")
    return record.model_copy(
        update={
            "company": normalize_text(record.company),
            "role": normalize_text(record.role),
            "location": location,
            "validation_errors": sorted(set(errors)),
        }
    )


def clean_records(records: list[Record]) -> list[Record]:
    return [clean_record(record) for record in records]
