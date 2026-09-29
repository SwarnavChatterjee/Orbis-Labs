"""Registry-backed source routing and approved collector registration."""

from collections.abc import Awaitable, Iterable
from typing import Protocol

from app.models.schemas import QueryPlan, Record, SourceDescriptor


class Collector(Protocol):
    def __call__(
        self, plan: QueryPlan, source: SourceDescriptor
    ) -> Iterable[Record] | Awaitable[Iterable[Record]]: ...


class CollectorRegistry:
    def __init__(self) -> None:
        self._collectors: dict[str, tuple[SourceDescriptor, Collector]] = {}

    def register(self, source: SourceDescriptor, collector: Collector) -> None:
        self._collectors[source.id] = (source, collector)

    def unregister(self, source_id: str) -> None:
        self._collectors.pop(source_id, None)

    def clear(self) -> None:
        self._collectors.clear()

    def descriptors(self) -> list[SourceDescriptor]:
        return [source for source, _ in self._collectors.values()]

    def route(self, intent: str, role: str | None = None) -> list[SourceDescriptor]:
        requested = {intent, intent.removesuffix("_search")}
        if role:
            requested.add(role.lower().replace(" ", "_"))
        return [
            source
            for source, _ in self._collectors.values()
            if requested.intersection(source.handles)
        ]

    def get(self, source_id: str) -> tuple[SourceDescriptor, Collector] | None:
        return self._collectors.get(source_id)


SOURCE_REGISTRY = CollectorRegistry()
DEMO_REGISTRY = CollectorRegistry()


def register_collector(source: SourceDescriptor, collector: Collector) -> None:
    SOURCE_REGISTRY.register(source, collector)


def route_sources(intent: str, role: str | None = None) -> list[SourceDescriptor]:
    """Select only sources with registered, approved collector functions."""

    return SOURCE_REGISTRY.route(intent, role)


def register_default_collectors() -> None:
    from app.collectors.greenhouse import collect_greenhouse
    from app.collectors.internshala import collect_internshala

    SOURCE_REGISTRY.register(
        SourceDescriptor(
            id="internshala",
            name="Internshala",
            kind="scrape",
            handles=["internship_search", "internship", "job_search", "job"],
            collector="app.collectors.internshala.collect_internshala",
            config={
                "base_url": "https://internshala.com",
                "search_url": "https://internshala.com/internships/",
            },
        ),
        collect_internshala,
    )
    SOURCE_REGISTRY.register(
        SourceDescriptor(
            id="gitlab_greenhouse",
            name="GitLab",
            kind="api",
            handles=["internship_search", "internship", "job_search", "job"],
            collector="app.collectors.greenhouse.collect_greenhouse",
            config={
                "board_token": "gitlab",
                "jobs_url": "https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true",
            },
        ),
        collect_greenhouse,
    )


def register_demo_collectors() -> None:
    from app.collectors.demo import collect_demo

    for source in SOURCE_REGISTRY.descriptors():
        DEMO_REGISTRY.register(source, collect_demo)


register_default_collectors()
register_demo_collectors()
