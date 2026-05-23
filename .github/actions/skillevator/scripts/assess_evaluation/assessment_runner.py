"""Concurrent orchestrator: runs grading calls via CopilotCommandRunner.

Each task runs in a fresh temporary directory that contains no skill folder,
so the skill being judged cannot influence its own verdict.
"""
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))

from assessment_parser import parse_assessment
from ..common.command_runner import CopilotCommandRunner
from ..common.evaluation_config import EvaluationConfig
from ..common.evaluation_models import Evaluation, Run
from grading_prompt_builder import build_grading_prompt


@dataclass
class AssessmentTask:
    evaluation: Evaluation
    run: Run


class AssessmentRunner:
    def __init__(self, config: EvaluationConfig, command_runner: CopilotCommandRunner) -> None:
        self._config  = config
        self._runner  = command_runner

    def run_task(self, task: AssessmentTask) -> AssessmentTask:
        """Grade one run; sets task.run.assessment in place and returns the task."""
        label  = (
            f"[grade] eval={task.evaluation.evaluation_name}"
            f" run={task.run.id}"
            f" include_skill={task.run.include_skill}"
        )
        print(f"{label} — running...")

        prompt = build_grading_prompt(task.evaluation, task.run)

        with tempfile.TemporaryDirectory() as tmp_dir:
            response = self._runner.run(prompt, Path(tmp_dir))

        task.run.assessment = parse_assessment(response.stdout_raw, task.evaluation)

        verdict = "✓ pass" if task.run.assessment.passed else "✗ fail"
        print(f"{label} — {verdict}")
        return task

    def run_all(self, tasks: list[AssessmentTask]) -> list[AssessmentTask]:
        """Grade all tasks concurrently; mutates each task.run.assessment in place."""
        with ThreadPoolExecutor() as executor:
            return list(executor.map(self.run_task, tasks))
