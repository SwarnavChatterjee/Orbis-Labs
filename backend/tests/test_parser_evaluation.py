from app.llm.evaluate import evaluate_cases, load_cases
from app.models.schemas import QueryFilters, QueryPlan


class FixturePlanner:
    def parse(self, raw_text: str) -> QueryPlan:
        case = next(item for item in load_cases() if item["input"] == raw_text)
        expected = case["expected"]
        filters = {}
        flags = []
        for key, value in expected.items():
            if key.startswith("filters."):
                filters[key.removeprefix("filters.")] = value
            elif key.startswith("ambiguity.") and value:
                flags.append({"field": key.removeprefix("ambiguity."), "reason": "fixture"})
        return QueryPlan(
            intent=expected.get("intent", "job_search"),
            filters=QueryFilters(**filters),
            target_count=expected.get("target_count", 20),
            ambiguity_flags=flags,
            sources=[],
        )


def test_evaluation_dataset_has_at_least_15_cases() -> None:
    assert len(load_cases()) >= 15


def test_evaluation_harness_checks_semantic_categories() -> None:
    report = evaluate_cases(FixturePlanner())
    assert report["cases"] == 16
    assert report["passed_cases"] == 16
    assert report["field_categories"]["intent"]["total"] > 0
    assert report["field_categories"]["sources_empty"]["passed"] == 1
