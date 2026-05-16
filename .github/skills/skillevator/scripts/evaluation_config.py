from dataclasses import dataclass, field
from pathlib import Path

_GITHUB = ".github"
_SKILLS = "skills"

# Exported — used by take_evaluation.py to build skill-specific sub-paths
EVALS        = "evals"
EVALUATIONS  = "evaluations"
EVALS_JSON   = "evals.json"


@dataclass
class EvaluationConfig:
    skill_name: str
    model: str = "gpt-4.1"
    allowed_tools: str = "shell(python)"
    times: int = 3

    project_root: Path                = field(init=False, repr=False)
    skillevator_root: Path            = field(init=False, repr=False)
    github_dir: Path                  = field(init=False, repr=False)
    skills_dir: Path                  = field(init=False, repr=False)
    skillevator_evaluations_dir: Path = field(init=False, repr=False)

    def __post_init__(self):
        _here = Path(__file__).resolve()
        self.skillevator_root             = _here.parents[1]
        self.project_root                 = _here.parents[4]
        self.github_dir                   = self.project_root / _GITHUB
        self.skills_dir                   = self.project_root / _GITHUB / _SKILLS
        self.skillevator_evaluations_dir  = self.skillevator_root / EVALUATIONS
