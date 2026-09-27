"""Registry-backed source routing and collector injection.

The initial registry is intentionally empty until the project owner finalizes
the supported sources. Tests and deployments register approved collectors.
"""

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


def register_collector(source: SourceDescriptor, collector: Collector) -> None:
    SOURCE_REGISTRY.register(source, collector)


def route_sources(intent: str, role: str | None = None) -> list[SourceDescriptor]:
    """Select only sources with registered, approved collector functions."""

    return SOURCE_REGISTRY.route(intent, role)
