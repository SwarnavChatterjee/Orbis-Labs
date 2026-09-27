from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


Intent = Literal["internship_search", "job_search"]
QueryStatus = Literal[
    "queued", "running", "planned", "collecting", "cleaning", "completed", "failed"
]


class AmbiguityFlag(BaseModel):
    field: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class QueryFilters(BaseModel):
    role: str | None = None
    location: str | None = None
    graduation_year: int | None = Field(default=None, ge=1900, le=2200)
    remote: bool | None = None


class QueryPlan(BaseModel):
    """Schema used by the API and OpenAI structured query parser."""

    intent: Intent
    filters: QueryFilters = Field(default_factory=QueryFilters)
    required_fields: list[str] = Field(default_factory=list)
    target_count: int = Field(default=20, ge=1, le=500)
    ambiguity_flags: list[AmbiguityFlag] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class SourceDescriptor(BaseModel):
    id: str
    name: str
    kind: Literal["scrape", "api"]
    handles: list[str] = Field(default_factory=list)
    collector: str
    config: dict[str, str] = Field(default_factory=dict)


class Stipend(BaseModel):
    amount: Decimal | None = None
    currency: str | None = None
    period: str | None = None


class Record(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company: str
    role: str
    location: str | None = None
    stipend: Stipend | None = None
    deadline: date | None = None
    source_url: HttpUrl
    source_name: str
    retrieved_at: datetime
    confidence: float = Field(ge=0, le=1)
    validation_errors: list[str] = Field(default_factory=list)


class ApiSuccess(BaseModel):
    success: Literal[True] = True
    data: object


class ApiError(BaseModel):
    success: Literal[False] = False
    error: str


class QuerySubmission(BaseModel):
    raw_text: str = Field(min_length=3, max_length=4000)

    @field_validator("raw_text", mode="before")
    @classmethod
    def trim_raw_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class QueryAccepted(BaseModel):
    query_id: UUID
    status: Literal["accepted"] = "accepted"


class QueryHistoryItem(BaseModel):
    id: UUID
    raw_text: str
    status: QueryStatus
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class QueryDetails(QueryHistoryItem):
    parsed_params: dict[str, object] | None = None
    record_count: int = 0


class Pagination(BaseModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)


class QueryHistoryPage(Pagination):
    items: list[QueryHistoryItem]


class QueryResultsPage(Pagination):
    items: list[dict[str, object]]


class QueryEventPayload(BaseModel):
    query_id: UUID
    status: QueryStatus
    timestamp: datetime
    message: str | None = None


class SourceInfo(BaseModel):
    id: str
    name: str
    kind: Literal["scrape", "api"]
    handles: list[str]

