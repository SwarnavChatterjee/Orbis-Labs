"""Small semantic evaluation harness for the query planner.

Run with: PYTHONPATH=backend python -m app.llm.evaluate
The checked-in fixture set contains no credentials or private user data.
"""

import json
from pathlib import Path

from app.llm.parser import QueryPlanner, parse_query, plan_is_unsupported
from app.models.schemas import QueryPlan


CASES_PATH = Path(__file__).with_name("evaluation_cases.json")


def load_cases() -> list[dict]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def _get_value(plan: QueryPlan, key: str):
    if key.startswith("filters."):
        return getattr(plan.filters, key.removeprefix("filters."))
    if key.startswith("ambiguity."):
        field = key.removeprefix("ambiguity.")
        if field == "intent":
            return plan_is_unsupported(plan)
        return any(flag.field == field for flag in plan.ambiguity_flags)
    if key == "sources_empty":
        return plan.sources == []
    return getattr(plan, key)


def evaluate_cases(planner: QueryPlanner, cases: list[dict] | None = None) -> dict:
    """Run semantic checks and return aggregate plus category-level results."""

    cases = cases if cases is not None else load_cases()
    checked = 0
    passed_cases = 0
    category_totals: dict[str, dict[str, int]] = {}
    failures = []
    for case in cases:
        case_failures = []
        try:
            plan = planner.parse(case["input"])
            # Successful return must satisfy the shared contract.
            QueryPlan.model_validate(plan.model_dump())
            for category, expected in case["expected"].items():
                result = _get_value(plan, category)
                bucket = category_totals.setdefault(category, {"passed": 0, "total": 0})
                bucket["total"] += 1
                checked += 1
                if result == expected:
                    bucket["passed"] += 1
                else:
                    case_failures.append(category)
        except Exception:
            case_failures.append("planner_error")
            bucket = category_totals.setdefault("planner_error", {"passed": 0, "total": 0})
            bucket["total"] += 1
            checked += 1
        if case_failures:
            failures.append({"name": case["name"], "categories": case_failures})
        else:
            passed_cases += 1
    return {
        "cases": len(cases),
        "passed_cases": passed_cases,
        "checked_fields": checked,
        "field_categories": category_totals,
        "failures": failures,
    }


class _ProductionPlanner:
    def parse(self, raw_text: str) -> QueryPlan:
        return parse_query(raw_text)


def main() -> int:
    report = evaluate_cases(_ProductionPlanner())
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed_cases"] == report["cases"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
