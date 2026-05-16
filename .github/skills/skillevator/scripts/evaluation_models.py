from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from evaluation_config import EvaluationConfig

@dataclass
class Assessment:
    grade: int
    feedback: str

@dataclass
class Criterion:
    id: int
    criterion: str

@dataclass
class Run:
    id: int
    include_skill: bool
    response: str
    tokens_input: Optional[str]
    tokens_output: Optional[str]
    tokens_cached: Optional[str]
    duration_seconds: Optional[float]
    assessment: Optional[Assessment]
    skill_name: Optional[str] = None
    success: Optional[bool] = None
    error: Optional[str] = None

@dataclass
class Evaluation:
    id: int
    evaluation_name: str
    prompt: str
    general_expectation: str
    criteria: list[Criterion]
    runs: list[Run] = field(default_factory=list)

@dataclass 
class ExtEvaluation(Evaluation):
    include_skill: bool = False

    def __init__(self, evaluation: Evaluation, include_skill: bool):
        self.id = evaluation.id
        self.evaluation_name = evaluation.evaluation_name
        self.prompt = evaluation.prompt
        self.general_expectation = evaluation.general_expectation
        self.criteria = evaluation.criteria
        self.runs = evaluation.runs
        self.include_skill = include_skill

@dataclass
class RunTask:
    evaluation: ExtEvaluation
    run_index: int
    total_runs: int
    iteration_dir: Path
    config: EvaluationConfig  # carries config into executor.map workers
    baseline_dir: Path        # skill-level dir; where baseline/ lives


@dataclass
class SkillEvaluation:
    skill_name: str
    evaluations: list[Evaluation] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "SkillEvaluation":
        return cls(
            skill_name=data["skill_name"],
            evaluations=[
                Evaluation(
                    id=e["id"],
                    evaluation_name=e["evaluation_name"],
                    prompt=e["prompt"],
                    general_expectation=e["general_expectation"],
                    criteria=[Criterion(**c) for c in e.get("criteria", [])],
                    runs=[
                        Run(
                            **{**r, "assessment": Assessment(**r["assessment"]) if r.get("assessment") else None}
                        )
                        for r in e.get("runs", [])
                    ],
                )
                for e in data.get("evaluations", [])
            ],
        )

    @classmethod
    def from_json_file(cls, path: Path) -> "SkillEvaluation":
        with open(path) as f:
            return cls.from_dict(json.load(f))

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json_file(self, path: Path) -> None:
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
