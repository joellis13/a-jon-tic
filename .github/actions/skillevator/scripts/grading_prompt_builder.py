"""Pure function: build the grading prompt from an (Evaluation, Run) pair.

No I/O, no side effects — deterministic given the same inputs.
"""
from evaluation_models import Evaluation, Run

_DIFF_CHAR_LIMIT = 2000


def _format_changes(changes: dict | None) -> str:
    if not changes:
        return "created:  none\nmodified: none\ndeleted:  none"

    created  = changes.get("created",  [])
    modified = changes.get("modified", [])
    deleted  = changes.get("deleted",  [])
    diffs    = changes.get("diffs",    {})

    lines = [
        f"created:  {', '.join(created)  if created  else 'none'}",
        f"modified: {', '.join(modified) if modified else 'none'}",
        f"deleted:  {', '.join(deleted)  if deleted  else 'none'}",
    ]

    if diffs:
        diff_text = "\n".join(f"--- {path} ---\n{diff}" for path, diff in diffs.items())
        if len(diff_text) > _DIFF_CHAR_LIMIT:
            diff_text = diff_text[:_DIFF_CHAR_LIMIT] + "\n... [truncated]"
        lines.append("\nDiffs:\n" + diff_text)

    return "\n".join(lines)


def build_grading_prompt(evaluation: Evaluation, run: Run) -> str:
    criteria_lines = "\n".join(f"{c.id}. {c.criterion}" for c in evaluation.criteria)
    criteria_json  = ",\n".join(
        f'    {{"id": {c.id}, "criterion": "{c.criterion}", "passed": <true or false>,'
        f' "evidence": "<direct quote or specific observation from the response above>"}}'
        for c in evaluation.criteria
    )

    return (
        "You are a strict evaluator. Read the Copilot response below and evaluate it "
        "against each criterion. Respond ONLY with the JSON object specified — no prose, "
        "no markdown fences, nothing else.\n"
        "\n"
        "## Original Prompt (what the user sent to Copilot)\n"
        f"{evaluation.prompt}\n"
        "\n"
        "## Expected Behavior\n"
        f"{evaluation.general_expectation}\n"
        "\n"
        "## Context\n"
        f"skill_triggered: {run.skill_triggered}\n"
        f"skill_name: {run.skill_name or 'none'}\n"
        f"include_skill: {run.include_skill}\n"
        "\n"
        "## File Changes\n"
        f"{_format_changes(run.changes)}\n"
        "\n"
        "## Copilot Response\n"
        f"{run.response}\n"
        "\n"
        "## Criteria to Evaluate\n"
        f"{criteria_lines}\n"
        "\n"
        "## Required JSON Output — respond with exactly this structure:\n"
        "{\n"
        '  "criteria_results": [\n'
        f"{criteria_json}\n"
        "  ]\n"
        "}"
    )
