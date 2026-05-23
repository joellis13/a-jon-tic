"""Compute per-evaluation and roll-up assessment statistics; write assessment_summary.json."""
import json
from datetime import datetime, timezone
from math import sqrt
from pathlib import Path

from evaluation_config import EvaluationConfig
from evaluation_models import SkillEvaluation

ASSESSMENT_SUMMARY_JSON = "assessment_summary.json"


def _bernoulli_stddev(pass_rate: float, n: int) -> float:
    if n == 0:
        return 0.0
    return sqrt(pass_rate * (1.0 - pass_rate) / n)


def _group_stats(runs: list) -> dict:
    assessed = [r for r in runs if r.assessment is not None]
    n = len(assessed)
    if n == 0:
        return {
            "runs": 0,
            "run_pass_rate": None,
            "run_pass_stddev": None,
            "skill_triggered_rate": None,
            "criteria_pass_rates": [],
        }

    run_passes = sum(1 for r in assessed if r.assessment.passed)
    run_pass_rate = run_passes / n
    triggered_rate = sum(1 for r in assessed if r.skill_triggered) / n

    # Per-criterion pass rates (keyed off the first assessed run's criteria order)
    criteria_pass_rates = []
    for cr_ref in assessed[0].assessment.criteria_results:
        passes = sum(
            1
            for r in assessed
            for cr in r.assessment.criteria_results
            if cr.id == cr_ref.id and cr.passed
        )
        criteria_pass_rates.append({
            "id":        cr_ref.id,
            "criterion": cr_ref.criterion,
            "pass_rate": round(passes / n, 4),
        })

    return {
        "runs":               n,
        "run_pass_rate":      round(run_pass_rate, 4),
        "run_pass_stddev":    round(_bernoulli_stddev(run_pass_rate, n), 4),
        "skill_triggered_rate": round(triggered_rate, 4),
        "criteria_pass_rates": criteria_pass_rates,
    }


def write_summary(skill_eval: SkillEvaluation, config: EvaluationConfig) -> Path:
    evaluations_out = []
    for evaluation in skill_eval.evaluations:
        with_stats = _group_stats(evaluation.with_skill_runs)
        base_stats = _group_stats(evaluation.baseline_runs)

        ws_rate = with_stats.get("run_pass_rate")
        bl_rate = base_stats.get("run_pass_rate")
        delta   = round(ws_rate - bl_rate, 4) if ws_rate is not None and bl_rate is not None else None

        evaluations_out.append({
            "id":              evaluation.id,
            "evaluation_name": evaluation.evaluation_name,
            "with_skill":      with_stats,
            "baseline":        base_stats,
            "delta":           delta,
        })

    ws_rates = [e["with_skill"]["run_pass_rate"] for e in evaluations_out if e["with_skill"].get("run_pass_rate") is not None]
    bl_rates = [e["baseline"]["run_pass_rate"]   for e in evaluations_out if e["baseline"].get("run_pass_rate")   is not None]
    deltas   = [e["delta"] for e in evaluations_out if e["delta"] is not None]

    summary = {
        "total_evaluations":       len(skill_eval.evaluations),
        "avg_with_skill_pass_rate": round(sum(ws_rates) / len(ws_rates), 4) if ws_rates else None,
        "avg_baseline_pass_rate":   round(sum(bl_rates) / len(bl_rates), 4) if bl_rates else None,
        "avg_delta":                round(sum(deltas)   / len(deltas),   4) if deltas   else None,
    }

    output = {
        "skill_name":   skill_eval.skill_name,
        "model":        config.model,
        "assessed_at":  datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evaluations":  evaluations_out,
        "summary":      summary,
    }

    out_path = config.skillevator_evaluations_dir / config.skill_name / ASSESSMENT_SUMMARY_JSON
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return out_path
