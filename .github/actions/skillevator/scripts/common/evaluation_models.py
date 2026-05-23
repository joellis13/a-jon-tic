from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from evaluation_config import EvaluationConfig

@dataclass
class CriterionResult:
    id: int
    criterion: str   # copied from the Criterion definition for self-contained records
    passed: bool     # the LLM's binary verdict for this criterion
    evidence: str    # the LLM's supporting quote or observation

@dataclass
class Assessment:
    passed: bool                             # all(r.passed for r in criteria_results) — always derived
    criteria_results: list[CriterionResult]  # one entry per Criterion

@dataclass
class Criterion:
    id: int
    criterion: str

@dataclass
class Run:
    id: int
    include_skill: bool
    response: str
    tokens_input: Optional[int]
    tokens_output: Optional[int]
    tokens_cached: Optional[int]
    duration_seconds: Optional[float]
    assessment: Optional[Assessment]
    skill_name: Optional[str] = None
    skill_triggered: Optional[bool] = None
    success: Optional[bool] = None
    error: Optional[str] = None
    changes: Optional[dict] = None

@dataclass
class Evaluation:
    id: int
    evaluation_name: str
    prompt: str
    general_expectation: str
    criteria: list[Criterion]
    seed_files: list[str] = field(default_factory=list)
    with_skill_runs: list[Run] = field(default_factory=list)
    baseline_runs:   list[Run] = field(default_factory=list)

@dataclass 
class ExtEvaluation(Evaluation):
    include_skill: bool = False

    def __init__(self, evaluation: Evaluation, include_skill: bool):
        super().__init__(
            id=evaluation.id,
            evaluation_name=evaluation.evaluation_name,
            prompt=evaluation.prompt,
            general_expectation=evaluation.general_expectation,
            criteria=evaluation.criteria,
            with_skill_runs=evaluation.with_skill_runs,
            baseline_runs=evaluation.baseline_runs,
        )
        self.include_skill = include_skill

@dataclass
class RunTask:
    evaluation: ExtEvaluation
    run_index: int
    total_runs: int
    iteration_dir: Path
    config: EvaluationConfig  # carries config into executor.map workers
    baseline_dir: Path        # skill-level dir; where baseline/ lives


def _parse_runs(e: dict, include_skill: bool, parse_run) -> list[Run]:
    """Load runs from either the new split keys or the legacy 'runs' list."""
    key = "with_skill_runs" if include_skill else "baseline_runs"
    if key in e:
        return [parse_run(r) for r in e[key]]
    # Legacy format: single 'runs' list — split by include_skill flag
    return [parse_run(r) for r in e.get("runs", []) if r.get("include_skill") == include_skill]


@dataclass
class SkillEvaluation:
    skill_name: str
    evaluations: list[Evaluation] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "SkillEvaluation":
        def parse_run(r: dict) -> Run:
            def parse_assessment(a: dict) -> Assessment:
                return Assessment(
                    passed=a["passed"],
                    criteria_results=[CriterionResult(**cr) for cr in a.get("criteria_results", [])],
                )
            return Run(**{**r, "assessment": parse_assessment(r["assessment"]) if r.get("assessment") else None})

        return cls(
            skill_name=data["skill_name"],
            evaluations=[
                Evaluation(
                    id=e["id"],
                    evaluation_name=e["evaluation_name"],
                    prompt=e["prompt"],
                    general_expectation=e["general_expectation"],
                    criteria=[Criterion(**c) for c in e.get("criteria", [])],
                    seed_files=e.get("seed_files", []),
                    with_skill_runs=_parse_runs(e, include_skill=True,  parse_run=parse_run),
                    baseline_runs=  _parse_runs(e, include_skill=False, parse_run=parse_run),
                )
                for e in data.get("evaluations", [])
            ],
        )

    @classmethod
    def from_json_file(cls, path: Path) -> "SkillEvaluation":
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json_file(self, path: Path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
