from app.models.schemas import SourceDescriptor


SOURCE_REGISTRY: list[SourceDescriptor] = [
    SourceDescriptor(
        id="internshala",
        name="Internshala",
        kind="scrape",
        handles=["internship", "software_engineering", "india"],
        collector="app.collectors.internshala.collect",
        config={"base_url": "https://internshala.com"},
    ),
    SourceDescriptor(
        id="gitlab_greenhouse",
        name="GitLab Careers",
        kind="api",
        handles=["internship", "job", "software_engineering", "remote"],
        collector="app.collectors.greenhouse.collect",
        config={
            "board_token": "gitlab",
            "endpoint": "https://boards-api.greenhouse.io/v1/boards/gitlab/jobs",
        },
    ),
]


def route_sources(intent: str, role: str | None = None) -> list[SourceDescriptor]:
    """Select registered sources deterministically; the LLM never chooses collectors."""

    requested = {intent, intent.removesuffix("_search")}
    if role:
        requested.add(role.lower().replace(" ", "_"))
    return [source for source in SOURCE_REGISTRY if requested.intersection(source.handles)]
