"""OpenAI-backed query planning with a small provider-independent interface."""

from typing import Protocol, runtime_checkable

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)
from pydantic import ValidationError

from app.core.config import settings
from app.models.schemas import QueryPlan


PARSER_PROMPT_VERSION = "v1"
SYSTEM_PROMPT = f"""You are the Orbis Labs query planner (prompt version {PARSER_PROMPT_VERSION}).

Interpret a request for internship or job search as a QueryPlan. You are only a
query interpreter: do not search the web, choose sources, or invent companies,
listings, URLs, salaries, deadlines, or collected records. Extract only stated
or directly implied values. Keep unknown optional filters null and use visible
ambiguity_flags whenever a meaningful filter is absent or uncertain. Return
only internship_search or job_search. For an unrelated or unsupported request,
use the closest allowed intent, leave filters unspecified, and add an ambiguity
flag with field "intent" explaining that the request is outside internship/job
search. The application routes sources separately; always return sources as an
empty list. Preserve the user's requested count when present, otherwise use the
schema default. Normalize only clear aliases, such as Bengaluru to Bangalore.
"""


@runtime_checkable
class QueryPlanner(Protocol):
    """Provider-independent interface used by API and worker code."""

    def parse(self, raw_text: str) -> QueryPlan: ...


class PlannerError(RuntimeError):
    """Base for safe, user-displayable planner failures."""


class PlannerConfigurationError(PlannerError):
    pass


class PlannerInputError(PlannerError):
    pass


class PlannerAuthenticationError(PlannerError):
    pass


class PlannerRateLimitError(PlannerError):
    pass


class PlannerTransportError(PlannerError):
    pass


class PlannerRefusalError(PlannerError):
    pass


class PlannerIncompleteResponseError(PlannerError):
    pass


class PlannerSchemaError(PlannerError):
    pass


class OpenAIQueryPlanner:
    def __init__(self, client: object, model: str):
        self.client = client
        self.model = model

    def parse(self, raw_text: str) -> QueryPlan:
        text = raw_text.strip()
        if not text:
            raise PlannerInputError("Enter a non-empty internship or job search request.")

        try:
            response = self.client.responses.parse(  # type: ignore[attr-defined]
                model=self.model,
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                text_format=QueryPlan,
            )
        except AuthenticationError as exc:
            raise PlannerAuthenticationError(
                "The query planner could not authenticate. Check backend OpenAI configuration."
            ) from exc
        except RateLimitError as exc:
            raise PlannerRateLimitError(
                "The query planner is temporarily rate limited. Please retry later."
            ) from exc
        except (APIConnectionError, APITimeoutError) as exc:
            raise PlannerTransportError(
                "The query planner could not connect. Please retry."
            ) from exc
        except APIStatusError as exc:
            raise PlannerTransportError(
                "The query planner could not complete the request. Please retry."
            ) from exc
        except Exception as exc:
            # Never relay SDK exception strings: they may contain request details.
            raise PlannerTransportError(
                "The query planner could not complete the request. Please retry."
            ) from exc

        if _response_contains_refusal(response):
            raise PlannerRefusalError("The request could not be planned safely.")
        if getattr(response, "status", None) == "incomplete":
            raise PlannerIncompleteResponseError(
                "The query planner returned an incomplete response. Please retry."
            )

        plan = getattr(response, "output_parsed", None)
        if plan is None:
            raise PlannerIncompleteResponseError(
                "The query planner returned no structured plan. Please retry."
            )
        try:
            if not isinstance(plan, QueryPlan):
                plan = QueryPlan.model_validate(plan)
        except (ValidationError, TypeError, ValueError) as exc:
            raise PlannerSchemaError(
                "The query planner returned a plan that did not match the required schema."
            ) from exc

        # Source selection is owned exclusively by deterministic Python routing.
        return plan.model_copy(update={"sources": []})


def _response_contains_refusal(response: object) -> bool:
    for output_item in getattr(response, "output", None) or []:
        for content in getattr(output_item, "content", None) or []:
            if getattr(content, "type", None) == "refusal":
                return True
    return False


def parse_query(raw_text: str, client: object | None = None) -> QueryPlan:
    """Compatibility function for existing worker callers."""

    if not raw_text.strip():
        raise PlannerInputError("Enter a non-empty internship or job search request.")
    if not settings.openai_model:
        raise PlannerConfigurationError(
            "OPENAI_MODEL must be configured before parsing queries."
        )
    if client is None and not settings.openai_api_key:
        raise PlannerConfigurationError(
            "The query planner is not configured. Add OPENAI_API_KEY to the backend environment."
        )
    openai_client = client or OpenAI(api_key=settings.openai_api_key)
    return OpenAIQueryPlanner(openai_client, settings.openai_model).parse(raw_text)


def plan_is_unsupported(plan: QueryPlan) -> bool:
    """Whether the model marked a request as outside the planner's domain."""

    return any(flag.field == "intent" for flag in plan.ambiguity_flags)
