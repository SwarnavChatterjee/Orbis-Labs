from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, JSON, Text
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(index=True, unique=True)
    google_subject: str | None = Field(default=None, index=True, unique=True)
    display_name: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class Project(SQLModel, table=True):
    __tablename__ = "projects"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID | None = Field(default=None, foreign_key="users.id", index=True)
    name: str
    created_at: datetime = Field(default_factory=utc_now)


class Source(SQLModel, table=True):
    __tablename__ = "sources"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    base_url: str


class QueryRecord(SQLModel, table=True):
    __tablename__ = "queries"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID | None = Field(default=None, foreign_key="projects.id", index=True)
    raw_text: str = Field(sa_column=Column(Text, nullable=False))
    parsed_params: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    status: str = Field(default="queued", index=True)
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class QueryEvent(SQLModel, table=True):
    __tablename__ = "query_events"

    id: int | None = Field(default=None, primary_key=True)
    query_id: UUID = Field(foreign_key="queries.id", index=True)
    status: str = Field(sa_column=Column(Text, nullable=False))
    message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class RecordRow(SQLModel, table=True):
    __tablename__ = "records"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    query_id: UUID = Field(foreign_key="queries.id", index=True)
    source_id: UUID | None = Field(default=None, foreign_key="sources.id", index=True)
    company: str
    role: str
    location: str | None = None
    stipend: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    deadline: date | None = None
    source_url: str
    retrieved_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    confidence: float | None = Field(default=None, ge=0, le=1)
    validation_errors: list[str] = Field(default_factory=list, sa_column=Column(JSON))
