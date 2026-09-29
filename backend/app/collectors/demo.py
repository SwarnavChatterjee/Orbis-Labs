"""Deterministic demo records for local product walkthroughs.

These records are intentionally fictional and are enabled only through the
development-only DEMO_MODE setting. They keep the full planner/queue/database/
results/CSV path demonstrable before live credentials and sources are enabled.
"""

from datetime import datetime, timezone

from app.collectors.common import limit_records
from app.models.schemas import QueryPlan, Record, SourceDescriptor


def collect_demo(plan: QueryPlan, source: SourceDescriptor) -> list[Record]:
    retrieved_at = datetime.now(timezone.utc)
    if source.id == "internshala":
        rows = [
            ("Northstar Analytics", "Software Engineering Intern", "Bengaluru, India", "32000"),
            ("Mango Labs", "Backend Engineering Intern", "Pune, India", "28000"),
            ("Blue Orbit Systems", "Data Platform Intern", "Remote, India", "30000"),
        ]
        base = "https://demo.orbis-labs.local/internshala"
    else:
        rows = [
            ("GitLab", "Frontend Engineer, University", "Remote", ""),
            ("GitLab", "Backend Engineer, Early Career", "Remote", ""),
            ("GitLab", "Data Engineering Intern", "London, UK", ""),
        ]
        base = "https://demo.orbis-labs.local/greenhouse"

    records = [
        Record(
            company=company,
            role=role,
            location=location,
            source_url=f"{base}/{index}",
            source_name=f"{source.name} (Demo)",
            retrieved_at=retrieved_at,
            confidence=0.94 if index % 2 else 0.89,
        )
        for index, (company, role, location, _stipend) in enumerate(rows, start=1)
    ]
    return limit_records(records, plan)
