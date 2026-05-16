import shutil
import tempfile
from pathlib import Path

from command_runner import CopilotCommandRunner
from evaluation_config import EvaluationConfig
from evaluation_models import Evaluation, Run, RunTask
from run_factory import RunFactory
from run_directory_writer import RunDirectoryWriter, WITH_SKILL, WITHOUT_SKILL


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

        skill_folder = WITH_SKILL if evaluation.include_skill else WITHOUT_SKILL
        run_dir = task.iteration_dir / evaluation.evaluation_name / skill_folder / str(run_index + 1)
        run_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            shutil.copytree(self.config.github_dir, tmp_path / ".github")

            if not evaluation.include_skill:
                shutil.rmtree(tmp_path / ".github" / "skills" / self.config.skill_name)

            before = {f for f in tmp_path.rglob("*") if f.is_file()}

            print(f"[Run {run_index + 1}/{total_runs}] command {evaluation.id}: {self._runner.build_command(prompt)}")
            response = self._runner.run(prompt, tmp_path)
            print(response.format_summary(evaluation.id, run_index, total_runs, evaluation.include_skill))

            run = self._factory.create(response, evaluation, run_index)
            self._writer.write(run_dir, response, evaluation)

            after = {f for f in tmp_path.rglob("*") if f.is_file()}
            for f in after - before:
                dest = run_dir / f.relative_to(tmp_path)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
                run.files.append(dest)

        return evaluation, run
