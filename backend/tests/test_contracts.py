from app.collectors.registry import SOURCE_REGISTRY, route_sources
from app.models.schemas import QueryPlan


def test_query_plan_defaults_are_schema_valid() -> None:
    plan = QueryPlan(intent="internship_search")
    assert plan.target_count == 20
    assert plan.ambiguity_flags == []


def test_registry_routes_internship_queries() -> None:
    sources = route_sources("internship_search", "software engineering")
    assert {source.id for source in sources} == {"internshala", "gitlab_greenhouse"}
    assert len(SOURCE_REGISTRY) == 2


def test_registry_routes_by_intent_without_role() -> None:
    assert {source.id for source in route_sources("internship_search")} == {
        "internshala",
        "gitlab_greenhouse",
    }
