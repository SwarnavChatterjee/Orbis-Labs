from types import SimpleNamespace

import pytest
from openai import AuthenticationError, RateLimitError

from app.core.config import settings
from app.llm.parser import (
    OpenAIQueryPlanner,
    PlannerConfigurationError,
    PlannerIncompleteResponseError,
    PlannerInputError,
    PlannerRefusalError,
    PlannerSchemaError,
    PlannerTransportError,
    SYSTEM_PROMPT,
    parse_query,
)
from app.models.schemas import QueryPlan


class FakeResponses:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.kwargs = None

    def parse(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.response


class FakeClient:
    def __init__(self, response=None, error=None):
        self.responses = FakeResponses(response, error)


class FakeAuthenticationError(AuthenticationError):
    def __init__(self):
        Exception.__init__(self, "secret-auth")


class FakeRateLimitError(RateLimitError):
    def __init__(self):
        Exception.__init__(self, "secret-rate")


def parsed(plan: QueryPlan):
    return SimpleNamespace(output_parsed=plan, output=[], status="completed")


def test_parser_uses_pydantic_structured_output_and_clears_model_sources() -> None:
    plan = QueryPlan(
        intent="internship_search",
        filters={"location": "India"},
        sources=["model-invented-source"],
    )
    client = FakeClient(parsed(plan))

    result = parse_query("Find internships in India", client=client)

    assert result.intent == "internship_search"
    assert result.filters.location == "India"
    assert result.sources == []
    assert client.responses.kwargs["text_format"] is QueryPlan
    assert client.responses.kwargs["input"][-1]["content"] == "Find internships in India"
    assert "always return sources as an" in SYSTEM_PROMPT


@pytest.mark.parametrize("raw_text", ["", "  \n "])
def test_empty_input_is_rejected_without_api_call(raw_text: str) -> None:
    with pytest.raises(PlannerInputError, match="non-empty"):
        parse_query(raw_text, client=FakeClient())


def test_missing_api_key_has_actionable_configuration_error(monkeypatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", None)
    with pytest.raises(PlannerConfigurationError, match="OPENAI_API_KEY"):
        parse_query("Find internships", client=None)


def test_missing_parsed_output_is_classified() -> None:
    with pytest.raises(PlannerIncompleteResponseError):
        OpenAIQueryPlanner(FakeClient(SimpleNamespace(output_parsed=None)), "test-model").parse(
            "Find internships"
        )


def test_incomplete_response_is_classified() -> None:
    response = SimpleNamespace(output_parsed=None, status="incomplete", output=[])
    with pytest.raises(PlannerIncompleteResponseError):
        OpenAIQueryPlanner(FakeClient(response), "test-model").parse("Find internships")


def test_refusal_response_is_classified() -> None:
    refusal = SimpleNamespace(
        output_parsed=None,
        status="completed",
        output=[SimpleNamespace(content=[SimpleNamespace(type="refusal")])],
    )
    with pytest.raises(PlannerRefusalError):
        OpenAIQueryPlanner(FakeClient(refusal), "test-model").parse("Find internships")


def test_invalid_structured_response_is_classified() -> None:
    response = SimpleNamespace(
        output_parsed={"intent": "invented", "filters": {}}, output=[], status="completed"
    )
    with pytest.raises(PlannerSchemaError):
        OpenAIQueryPlanner(FakeClient(response), "test-model").parse("Find internships")


def test_provider_exception_text_is_not_exposed() -> None:
    planner = OpenAIQueryPlanner(FakeClient(error=RuntimeError("secret-token")), "test-model")
    with pytest.raises(PlannerTransportError) as error:
        planner.parse("Find internships")
    assert "secret-token" not in str(error.value)
    assert "retry" in str(error.value)


@pytest.mark.parametrize(
    ("provider_error", "safe_error"),
    [
        (FakeAuthenticationError, "PlannerAuthenticationError"),
        (FakeRateLimitError, "PlannerRateLimitError"),
    ],
)
def test_authentication_and_rate_limit_errors_are_classified(provider_error, safe_error) -> None:
    from app.llm import parser

    planner = OpenAIQueryPlanner(FakeClient(error=provider_error()), "test-model")
    error_class = getattr(parser, safe_error)
    with pytest.raises(error_class) as error:
        planner.parse("Find internships")
    assert "secret-" not in str(error.value)
