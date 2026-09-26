from types import SimpleNamespace

from app.llm.parser import parse_query
from app.models.schemas import QueryPlan


class FakeResponses:
    def parse(self, **kwargs):
        assert kwargs["text_format"] is QueryPlan
        assert kwargs["input"][-1]["content"] == "Find internships in India"
        return SimpleNamespace(
            output_parsed=QueryPlan(
                intent="internship_search",
                filters={"location": "India"},
            )
        )


class FakeClient:
    responses = FakeResponses()


def test_parser_uses_pydantic_structured_output() -> None:
    plan = parse_query("Find internships in India", client=FakeClient())
    assert plan.intent == "internship_search"
    assert plan.filters.location == "India"

