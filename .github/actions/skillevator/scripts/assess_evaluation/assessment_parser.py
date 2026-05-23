"""Pure function: parse the LLM grading response into an Assessment.

No I/O, no side effects.  Gracefully degrades on any parse failure so that
every run always receives an Assessment — failures are visible, not silent.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))

from ..common.evaluation_models import Assessment, CriterionResult, Evaluation


def parse_assessment(raw_stdout: str, evaluation: Evaluation) -> Assessment:
    stripped = _strip_fences(raw_stdout.strip())

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as exc:
        return _failure_assessment(
            evaluation,
            f"[json parse error: {exc}] {raw_stdout[:200]}",
        )

    raw_results = data.get("criteria_results")
    if not isinstance(raw_results, list):
        return _failure_assessment(
            evaluation,
            f"[missing or non-list criteria_results] {raw_stdout[:200]}",
        )

    criterion_map = {c.id: c.criterion for c in evaluation.criteria}
    parsed: list[CriterionResult] = []
    seen_ids: set[int] = set()

    for raw in raw_results:
        try:
            cr_id        = int(raw["id"])
            passed_raw   = raw["passed"]
            passed       = bool(passed_raw) if not isinstance(passed_raw, bool) else passed_raw
            evidence     = str(raw.get("evidence", ""))
            criterion_text = raw.get("criterion") or criterion_map.get(cr_id, f"criterion {cr_id}")
            parsed.append(CriterionResult(id=cr_id, criterion=criterion_text, passed=passed, evidence=evidence))
            seen_ids.add(cr_id)
        except (KeyError, TypeError, ValueError) as exc:
            cr_id = int(raw.get("id", len(parsed) + 1)) if isinstance(raw, dict) else len(parsed) + 1
            parsed.append(CriterionResult(
                id=cr_id,
                criterion=criterion_map.get(cr_id, f"criterion {cr_id}"),
                passed=False,
                evidence=f"[malformed entry: {exc}]",
            ))
            seen_ids.add(cr_id)

    # Fill any criteria absent from the response
    for c in evaluation.criteria:
        if c.id not in seen_ids:
            parsed.append(CriterionResult(
                id=c.id,
                criterion=c.criterion,
                passed=False,
                evidence="[missing from grader response]",
            ))

    parsed.sort(key=lambda r: r.id)

    return Assessment(
        passed=all(r.passed for r in parsed),
        criteria_results=parsed,
    )


def _strip_fences(text: str) -> str:
    text = re.sub(r"^```[a-z]*\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n?```$",       "", text, flags=re.MULTILINE)
    return text.strip()


def _failure_assessment(evaluation: Evaluation, evidence: str) -> Assessment:
    results = [
        CriterionResult(id=c.id, criterion=c.criterion, passed=False, evidence=evidence)
        for c in evaluation.criteria
    ]
    return Assessment(passed=False, criteria_results=results)
