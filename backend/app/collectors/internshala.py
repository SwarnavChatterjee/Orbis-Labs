"""Internshala HTML collector with a fixture-friendly parser."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from app.collectors.common import compact, limit_records
from app.models.schemas import QueryPlan, Record, SourceDescriptor


def parse_internshala_html(
    html: str, source: SourceDescriptor, retrieved_at: datetime | None = None
) -> list[Record]:
    retrieved = retrieved_at or datetime.now(timezone.utc)
    soup = BeautifulSoup(html, "html.parser")
    records: list[Record] = []
    for card in soup.select(".individual_internship, [data-internship-id], .internship_meta"):
        title_node = card.select_one(".job-title, .profile, [data-field='role']")
        company_node = card.select_one(".company-name, .organization, [data-field='company']")
        location_node = card.select_one(".location, .locations, [data-field='location']")
        link = card.select_one("a[href]")
        if not title_node or not company_node or not link:
            continue
        href = link.get("href", "")
        if href.startswith("/"):
            href = source.config.get("base_url", "https://internshala.com").rstrip("/") + href
        if not href.startswith("http"):
            continue
        records.append(
            Record(
                company=compact(company_node.get_text(" ", strip=True)) or "Unknown company",
                role=compact(title_node.get_text(" ", strip=True)) or "Unknown role",
                location=compact(location_node.get_text(" ", strip=True)) if location_node else None,
                source_url=href,
                source_name=source.name,
                retrieved_at=retrieved,
                confidence=0.82,
            )
        )
    return records


def collect_internshala(
    plan: QueryPlan, source: SourceDescriptor, client: httpx.Client | None = None
) -> list[Record]:
    owns_client = client is None
    http_client = client or httpx.Client(timeout=20, follow_redirects=True)
    try:
        response = http_client.get(source.config["search_url"])
        response.raise_for_status()
        return limit_records(parse_internshala_html(response.text, source), plan)
    finally:
        if owns_client:
            http_client.close()
