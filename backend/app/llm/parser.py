from openai import OpenAI

from app.core.config import settings
from app.models.schemas import QueryPlan


SYSTEM_PROMPT = """You are the Orbis Labs query planner.

Convert the user's request into a QueryPlan. Extract only information present
or directly implied by the request. Do not invent companies, listings, URLs, or
records. If a filter is missing or uncertain, leave it null and add an
ambiguity flag. The application will choose data sources separately.
"""


def parse_query(raw_text: str, client: OpenAI | None = None) -> QueryPlan:
    """Parse one request into the shared schema using OpenAI Structured Outputs."""

    if not settings.openai_model:
        raise RuntimeError("OPENAI_MODEL must be configured before parsing queries")

    openai_client = client or OpenAI(api_key=settings.openai_api_key)
    response = openai_client.responses.parse(
        model=settings.openai_model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": raw_text},
        ],
        text_format=QueryPlan,
    )

    if response.output_parsed is None:
        raise RuntimeError("OpenAI returned no structured query plan")
    return response.output_parsed

