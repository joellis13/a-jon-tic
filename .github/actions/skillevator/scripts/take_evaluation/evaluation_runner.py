import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))

import file_tracker
from command_runner import CopilotCommandRunner
from evaluation_config import EvaluationConfig, EVALS
from evaluation_models import Evaluation, Run, RunTask
from run_factory import RunFactory
from run_directory_writer import RunDirectoryWriter, BASELINE


class EvaluationRunner:
    """Orchestrates a single evaluation run end-to-end.

    Wires together CopilotCommandRunner, RunFactory, and RunDirectoryWriter.
    Replaces the former run_prompt + run_prompt_in_temp_dir functions.

    Receives all collaborators via constructor injection (DIP): callers can
    substitute fakes for any collaborator without touching this class.
    """

    def __init__(
        self,
        config: EvaluationConfig,
        runner: CopilotCommandRunner,
        factory: RunFactory,
        writer: RunDirectoryWriter,
    ) -> None:
        self.config = config
        self._runner = runner
        self._factory = factory
        self._writer = writer

    def run_task(self, task: RunTask) -> tuple[Evaluation, Run]:
        evaluation = task.evaluation
        run_index = task.run_index
        total_runs = task.total_runs
        prompt = evaluation.prompt

        if evaluation.include_skill:
            run_dir = task.iteration_dir / evaluation.evaluation_name / str(run_index + 1)
        else:
            run_dir = task.baseline_dir / BASELINE / evaluation.evaluation_name / str(run_index + 1)
        run_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            shutil.copytree(self.config.github_dir, tmp_path / ".github")

            if not evaluation.include_skill:
                shutil.rmtree(tmp_path / ".github" / "skills" / self.config.skill_name)

            for rel_path in evaluation.seed_files:
                src = self.config.skills_dir / self.config.skill_name / EVALS / evaluation.evaluation_name / rel_path
                dest = tmp_path / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)

            before = file_tracker.snapshot(tmp_path)

            print(f"[Run {run_index + 1}/{total_runs}] command {evaluation.id}: {self._runner.build_command(prompt)}")
            response = self._runner.run(prompt, tmp_path)
            print(response.format_summary(evaluation.id, evaluation.evaluation_name, evaluation.prompt, run_index, total_runs, evaluation.include_skill))

            after = file_tracker.snapshot(tmp_path)
            changes = file_tracker.compute_changes(before, after)

            for rel_path in changes["modified"]:
                seed_src = self.config.skills_dir / self.config.skill_name / EVALS / evaluation.evaluation_name / rel_path
                changes["diffs"][rel_path] = file_tracker.generate_diff(seed_src, tmp_path / rel_path)
            for rel_path in changes["created"]:
                changes["diffs"][rel_path] = file_tracker.generate_creation_diff(tmp_path / rel_path)

            run = self._factory.create(response, evaluation, run_index, changes)
            self._writer.write(run_dir, response, evaluation, self.config.model, self.config.allowed_tools, changes)

            for rel_path in changes["created"] + changes["modified"]:
                src = tmp_path / rel_path
                dest = run_dir / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)

        return evaluation, run
