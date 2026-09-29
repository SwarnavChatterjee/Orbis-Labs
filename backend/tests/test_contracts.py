from app.collectors.registry import CollectorRegistry
from app.models.schemas import QueryPlan, SourceDescriptor


def test_query_plan_defaults_are_schema_valid() -> None:
    plan = QueryPlan(intent="internship_search")
    assert plan.target_count == 20
    assert plan.ambiguity_flags == []


def test_registry_routes_only_registered_sources() -> None:
    registry = CollectorRegistry()
    source = SourceDescriptor(
        id="fixture_source",
        name="Fixture Source",
        kind="api",
        handles=["internship", "software_engineering"],
        collector="fixture.collect",
    )
    registry.register(source, lambda _plan, _source: [])
    sources = registry.route("internship_search", "software engineering")
    assert [item.id for item in sources] == ["fixture_source"]


def test_default_registry_selects_only_the_approved_sources() -> None:
    from app.collectors.registry import route_sources

    assert [source.id for source in route_sources("internship_search")] == [
        "internshala",
        "gitlab_greenhouse",
    ]
