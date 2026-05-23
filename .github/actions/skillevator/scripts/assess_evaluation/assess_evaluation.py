"""CLI entrypoint for the grader — mirrors take_evaluation.py's structure.

Loads evals.json produced by the taker, grades every unassessed run concurrently
using the Copilot CLI as an LLM judge, writes assessments back to evals.json, and
produces assessment_summary.json alongside it.
"""
import argparse
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))

from assessment_runner import AssessmentRunner, AssessmentTask
from assessment_summary_writer import write_summary
from ..common.command_runner import CopilotCommandRunner
from ..common.evaluation_config import EvaluationConfig, EVALS_JSON
from ..common.evaluation_models import SkillEvaluation


def _load_skill_eval(config: EvaluationConfig) -> tuple[SkillEvaluation, Path]:
    path = config.skillevator_evaluations_dir / config.skill_name / EVALS_JSON
    return SkillEvaluation.from_json_file(path), path


def _build_work_list(skill_eval: SkillEvaluation, force: bool) -> list[AssessmentTask]:
    tasks = []
    for evaluation in skill_eval.evaluations:
        for run in evaluation.with_skill_runs + evaluation.baseline_runs:
            if force or run.assessment is None:
                tasks.append(AssessmentTask(evaluation=evaluation, run=run))
    return tasks


def _fmt_rate(n_pass: int, n_total: int, rate: float | None) -> str:
    if rate is None:
        return "  —   "
    symbol = "✓" if rate == 1.0 else "✗" if rate == 0.0 else "~"
    return f"{n_pass}/{n_total} {symbol}"


def _print_console_summary(skill_eval: SkillEvaluation) -> None:
    SEP = "=" * 66
    print(f"\n{SEP}")
    print(f"Assessment Summary — {skill_eval.skill_name}")
    print(SEP)
    print(f" {'#':>2}  {'Eval Name':<24}  {'With-Skill':>10}  {'Baseline':>8}  {'Delta':>6}  {'Triggered':>9}")

    all_ws_rates = []
    all_bl_rates = []
    weak_criteria = []  # (eval_name, criterion_text, pass_rate, passes, n)

    for e in skill_eval.evaluations:
        ws_runs = [r for r in e.with_skill_runs if r.assessment is not None]
        bl_runs = [r for r in e.baseline_runs  if r.assessment is not None]

        ws_n    = len(ws_runs)
        bl_n    = len(bl_runs)
        ws_pass = sum(1 for r in ws_runs if r.assessment and r.assessment.passed)
        bl_pass = sum(1 for r in bl_runs if r.assessment and r.assessment.passed)
        ws_rate = (ws_pass / ws_n) if ws_n else None
        bl_rate = (bl_pass / bl_n) if bl_n else None
        triggered = sum(1 for r in ws_runs if r.skill_triggered)

        delta_str = f"{ws_rate - bl_rate:+.2f}" if ws_rate is not None and bl_rate is not None else "  —  "
        print(
            f" {e.id:>2}  {e.evaluation_name:<24}  "
            f"{_fmt_rate(ws_pass, ws_n, ws_rate):>10}  "
            f"{_fmt_rate(bl_pass, bl_n, bl_rate):>8}  "
            f"{delta_str:>6}  "
            f"{triggered}/{ws_n:>7}"
        )

        if ws_rate is not None:
            all_ws_rates.append(ws_rate)
        if bl_rate is not None:
            all_bl_rates.append(bl_rate)

        # Collect criteria that didn't pass every with-skill run
        first_results = ws_runs[0].assessment.criteria_results if ws_runs and ws_runs[0].assessment else None
        if first_results:
            for cr_ref in first_results:
                passes = sum(
                    1 for r in ws_runs
                    for cr in (r.assessment.criteria_results if r.assessment and r.assessment.criteria_results else [])
                    if cr.id == cr_ref.id and cr.passed
                )
                rate = passes / ws_n
                if rate < 1.0:
                    weak_criteria.append((e.evaluation_name, cr_ref.criterion, rate, passes, ws_n))

    print("-" * 66)
    avg_ws    = sum(all_ws_rates) / len(all_ws_rates) if all_ws_rates else None
    avg_bl    = sum(all_bl_rates) / len(all_bl_rates) if all_bl_rates else None
    avg_delta = avg_ws - avg_bl if avg_ws is not None and avg_bl is not None else None

    ws_str = f"{avg_ws:.2f}"    if avg_ws    is not None else "—"
    bl_str = f"{avg_bl:.2f}"    if avg_bl    is not None else "—"
    d_str  = f"{avg_delta:+.2f}" if avg_delta is not None else "—"
    print(f"    {'Avg pass rate':<24}  {ws_str:>10}  {bl_str:>8}  {d_str:>6}")
    print(SEP)

    if weak_criteria:
        print("\nWeakest criteria (with-skill):")
        for eval_name, criterion, _rate, passes, total in sorted(weak_criteria, key=lambda x: x[2]):
            print(f'  {eval_name} / "{criterion}"  {passes}/{total} runs passing')

    print(SEP)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assess skill evaluation runs using the Copilot CLI as an LLM judge.")
    parser.add_argument("--skill-name", default="hello-user", help="Name of the skill to assess")
    parser.add_argument("--model",      default="gpt-4.1",    help="Copilot model to use for grading")
    parser.add_argument("--timeout",    type=int, default=60, help="Seconds before a grading call is killed (default: 60)")
    parser.add_argument("--force",      action="store_true",  help="Re-grade runs that already have an assessment")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = EvaluationConfig(skill_name=args.skill_name, model=args.model, timeout=args.timeout)

    skill_eval, evals_path = _load_skill_eval(config)
    tasks = _build_work_list(skill_eval, args.force)

    if not tasks:
        print("All runs already assessed.")
        return

    print(f"Assessing {len(tasks)} run(s) for '{args.skill_name}'...")
    runner = AssessmentRunner(config, CopilotCommandRunner(config))
    runner.run_all(tasks)

    # Mutations happened in place on the original run objects; deep copy before writing
    updated = copy.deepcopy(skill_eval)
    updated.to_json_file(evals_path)

    summary_path = write_summary(updated, config)
    print(f"\nAssessment summary written to: {summary_path}")

    _print_console_summary(updated)


if __name__ == "__main__":
    main()
