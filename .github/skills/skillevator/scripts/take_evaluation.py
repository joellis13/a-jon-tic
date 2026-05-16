import argparse
from concurrent.futures import ThreadPoolExecutor
import copy
from pprint import pprint
from pathlib import Path

from command_runner import CopilotCommandRunner
from evaluation_config import EvaluationConfig, EVALS, EVALS_JSON
from evaluation_models import ExtEvaluation, SkillEvaluation, Evaluation, RunTask
from evaluation_runner import EvaluationRunner
from run_factory import RunFactory
from run_directory_writer import RunDirectoryWriter


def get_results_dir(config: EvaluationConfig) -> Path:
    skill_eval_dir = config.skillevator_evaluations_dir / config.skill_name
    base_name = skill_eval_dir / "iteration"
    counter = 1
    while True:
        directory_name = Path(f"{base_name}-{counter:02d}")
        if not directory_name.exists():
            directory_name.mkdir(parents=True)
            print(f"Created: {directory_name}")
            return directory_name
        counter += 1


def setup_eval_location(config: EvaluationConfig) -> Path:
    skill_evaluation_directory = config.skillevator_evaluations_dir / config.skill_name
    skill_evaluation_directory.mkdir(parents=True, exist_ok=True)
    return skill_evaluation_directory / EVALS_JSON


def get_evals(config: EvaluationConfig) -> SkillEvaluation:
    skill_eval_file = config.skills_dir / config.skill_name / EVALS / EVALS_JSON
    return SkillEvaluation.from_json_file(skill_eval_file)


def get_split_evaluations(evaluations: list[Evaluation]) -> list[ExtEvaluation]:
    return [ExtEvaluation(e, include) for e in evaluations for include in (True, False)]


def run_prompts(evaluations: list[Evaluation], iteration_dir: Path, eval_runner: EvaluationRunner) -> list[Evaluation]:
    """Run each evaluation multiple times concurrently."""
    config = eval_runner.config
    tasks = [
        RunTask(evaluation, run_num, config.times, iteration_dir, config)
        for evaluation in get_split_evaluations(evaluations)
        for run_num in range(config.times)
    ]

    with ThreadPoolExecutor() as executor:
        results = list(executor.map(eval_runner.run_task, tasks))

    evaluation_runs = {eval.id: [] for eval in evaluations}
    for evaluation, run in results:
        evaluation_runs[evaluation.id].append(run)

    for evaluation in evaluations:
        evaluation.runs.extend(evaluation_runs[evaluation.id])

    return evaluations


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run skill evaluations with the Copilot CLI.")
    parser.add_argument("--skill-name", default="hello-user", help="Name of the skill to evaluate")
    parser.add_argument("--model",      default="gpt-4.1",    help="Copilot model to use")
    parser.add_argument("--times", type=int, default=3,       help="Number of runs per evaluation")
    return parser.parse_args()


def main():
    args = parse_args()
    config = EvaluationConfig(skill_name=args.skill_name, model=args.model, times=args.times)
    eval_runner = EvaluationRunner(config, CopilotCommandRunner(config), RunFactory(), RunDirectoryWriter())
    eval_location = setup_eval_location(config)
    iteration_dir = get_results_dir(config)
    skill_eval = get_evals(config)
    evaluations = skill_eval.evaluations
    evaluations_with_runs = run_prompts(evaluations, iteration_dir, eval_runner)
    pprint([{"id": e.id, "runs_count": len(e.runs)} for e in evaluations_with_runs])
    updated_skill_eval = copy.deepcopy(skill_eval)
    updated_skill_eval.evaluations = evaluations_with_runs
    updated_skill_eval.to_json_file(eval_location)


if __name__ == "__main__":
    main()
