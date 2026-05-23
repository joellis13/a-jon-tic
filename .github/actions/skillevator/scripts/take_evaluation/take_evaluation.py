import argparse
from concurrent.futures import ThreadPoolExecutor
import copy
import json
import shutil
import sys
from pathlib import Path
from pprint import pprint

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))

from command_runner import CopilotCommandRunner
from evaluation_config import EvaluationConfig, EVALS, EVALS_JSON
from evaluation_models import ExtEvaluation, SkillEvaluation, Evaluation, RunTask
from evaluation_runner import EvaluationRunner
from run_factory import RunFactory
from run_directory_writer import RunDirectoryWriter, RESPONSE_FILE, BASELINE, META_FILE


def _baseline_is_stale(eval_name: str, baseline_dir: Path, model: str, prompt: str, allowed_tools: list[str], seed_files: list[str]) -> bool:
    """Return True if the cached baseline was run with a different model, prompt, allowed_tools, or seed_files."""
    meta_path = baseline_dir / BASELINE / eval_name / "1" / META_FILE
    if not meta_path.exists():
        return False
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    cached_model = meta.get("model")
    cached_prompt = meta.get("prompt")
    if cached_model is None or cached_prompt is None:
        return False  # pre-feature meta; can't determine staleness, assume valid
    cached_tools = meta.get("allowed_tools")
    cached_seeds = meta.get("seed_files")
    return cached_model != model or cached_prompt != prompt or cached_tools != allowed_tools or cached_seeds != seed_files


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


def run_prompts(evaluations: list[Evaluation], iteration_dir: Path, baseline_dir: Path, eval_runner: EvaluationRunner) -> list[Evaluation]:
    """Run each evaluation multiple times concurrently."""
    config = eval_runner.config
    tasks = []
    for evaluation in get_split_evaluations(evaluations):
        if not evaluation.include_skill:
            stale_dir = baseline_dir / BASELINE / evaluation.evaluation_name
            if stale_dir.exists() and _baseline_is_stale(evaluation.evaluation_name, baseline_dir, config.model, evaluation.prompt, config.allowed_tools, evaluation.seed_files):
                shutil.rmtree(stale_dir)
                print(f"[baseline] Stale baseline removed for '{evaluation.evaluation_name}' (model, prompt, tools, or seed_files changed) — will rerun")
        for run_num in range(config.times):
            if not evaluation.include_skill:
                run_dir = baseline_dir / BASELINE / evaluation.evaluation_name / str(run_num + 1)
                if (run_dir / RESPONSE_FILE).exists():
                    continue  # baseline already on disk; skip re-run
            tasks.append(RunTask(evaluation, run_num, config.times, iteration_dir, config, baseline_dir))

    with ThreadPoolExecutor() as executor:
        results = list(executor.map(eval_runner.run_task, tasks))

    evaluation_map = {e.id: e for e in evaluations}
    for evaluation, run in results:
        target = evaluation_map[evaluation.id]
        if run.include_skill:
            target.with_skill_runs.append(run)
        else:
            target.baseline_runs.append(run)

    return evaluations


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run skill evaluations with the Copilot CLI.")
    parser.add_argument("--skill-name",  default="hello-user", help="Name of the skill to evaluate")
    parser.add_argument("--allow-tool",  dest="allowed_tools", action="append", default=[],
                        metavar="TOOL",  help="Tool to allow (repeat for multiple, e.g. --allow-tool shell(python))")
    parser.add_argument("--model",       default="gpt-4.1",    help="Copilot model to use")
    parser.add_argument("--times",   type=int, default=3,   help="Number of runs per evaluation")
    parser.add_argument("--timeout", type=int, default=120, help="Seconds before a CLI call is killed (default: 120)")
    return parser.parse_args()


def main():
    args = parse_args()
    config = EvaluationConfig(skill_name=args.skill_name, allowed_tools=args.allowed_tools, model=args.model, times=args.times, timeout=args.timeout)
    eval_runner = EvaluationRunner(config, CopilotCommandRunner(config), RunFactory(), RunDirectoryWriter())
    eval_location = setup_eval_location(config)
    baseline_dir = config.skillevator_evaluations_dir / config.skill_name
    iteration_dir = get_results_dir(config)
    skill_eval = get_evals(config)
    evaluations = skill_eval.evaluations
    evaluations_with_runs = run_prompts(evaluations, iteration_dir, baseline_dir, eval_runner)
    pprint([{"id": e.id, "name": e.evaluation_name, "with_skill": len(e.with_skill_runs), "baseline": len(e.baseline_runs)} for e in evaluations_with_runs])
    updated_skill_eval = copy.deepcopy(skill_eval)
    updated_skill_eval.evaluations = evaluations_with_runs
    updated_skill_eval.to_json_file(eval_location)


if __name__ == "__main__":
    main()
