import json
from datetime import datetime, timezone
from pathlib import Path

from app.collectors.common import limit_records
from app.collectors.greenhouse import parse_greenhouse_payload
from app.collectors.internshala import parse_internshala_html
from app.collectors.registry import SOURCE_REGISTRY
from app.models.schemas import QueryFilters, QueryPlan
from app.processing.clean import clean_record
from app.processing.dedup import deduplicate_records


FIXTURES = Path(__file__).parents[1] / "fixtures"


def test_default_registry_contains_the_two_approved_sources() -> None:
    assert [source.id for source in SOURCE_REGISTRY.descriptors()] == [
        "internshala",
        "gitlab_greenhouse",
    ]


def test_greenhouse_fixture_parser_and_filters() -> None:
    payload = json.loads((FIXTURES / "greenhouse_gitlab.json").read_text())
    source = SOURCE_REGISTRY.get("gitlab_greenhouse")[0]
    plan = QueryPlan(intent="job_search", filters=QueryFilters(role="backend", location="India"))
    records = parse_greenhouse_payload(payload, source, datetime.now(timezone.utc))
    assert len(records) == 2
    assert [record.role for record in limit_records(records, plan)] == ["Backend Engineer"]


def test_internshala_fixture_parser_normalizes_relative_urls() -> None:
    source = SOURCE_REGISTRY.get("internshala")[0]
    html = (FIXTURES / "internshala.html").read_text()
    records = parse_internshala_html(html, source, datetime.now(timezone.utc))
    assert len(records) == 2
    assert str(records[0].source_url) == "https://internshala.com/internship/detail/software-engineering-internship-1001"


def test_cleaning_normalizes_location_and_dedup_keeps_highest_confidence() -> None:
    source = SOURCE_REGISTRY.get("internshala")[0]
    records = parse_internshala_html((FIXTURES / "internshala.html").read_text(), source)
    cleaned = [clean_record(record) for record in records]
    duplicate = cleaned[0].model_copy(update={"confidence": 0.99, "source_url": "https://example.com/canonical"})
    result = deduplicate_records([cleaned[0], duplicate, cleaned[1]])
    assert len(result) == 2
    assert any(str(record.source_url) == "https://example.com/canonical" for record in result)
    assert next(record for record in result if record.company == "Orbis Labs").location == "Bangalore"
