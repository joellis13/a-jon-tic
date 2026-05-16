
from concurrent.futures import ThreadPoolExecutor
import copy
import json
from pprint import pprint
from pathlib import Path
import shutil
import subprocess
import tempfile

from evaluation_config import EvaluationConfig, EVALS, EVALS_JSON
from evaluation_models import ExtEvaluation, SkillEvaluation, Evaluation, Run, RunTask
from copilot_models import CopilotResponse

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

def run_prompt(task: RunTask, cwd: Path) -> tuple[Evaluation, Run, Path]:
    """Run a single prompt and return the evaluation, run result, and output directory."""
    evaluation = task.evaluation
    run_index = task.run_index
    total_runs = task.total_runs
    config = task.config
    eval_id = evaluation.id
    prompt = evaluation.prompt
    command = f"copilot --allow-tool=\"{config.allowed_tools}\" --model {config.model} -p \"{prompt}\""
    print(f"[Run {run_index + 1}/{total_runs}] command {eval_id}: {command}")

    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        encoding='utf-8',
        cwd=str(cwd)
    )

    response = CopilotResponse.from_subprocess_result(result)

    print("\n==================================================")
    print(f"result {eval_id} (run {run_index + 1}/{total_runs}): ")
    print("skill_name: " + str(response.skill_name))
    print("success: " + str(response.success))
    print("error: " + str(response.error))
    print("include_skill: " + str(evaluation.include_skill))
    print("message: " + str(response.message))
    print("tokens_input: " + str(response.tokens_input))
    print("tokens_output: " + str(response.tokens_output))
    print("tokens_cached: " + str(response.tokens_cached))
    print("duration_seconds: " + str(response.duration_seconds))
    print("==================================================\n")

    skill_folder = "with_skill" if evaluation.include_skill else "without_skill"
    run_dir = task.iteration_dir / evaluation.evaluation_name / skill_folder / str(run_index + 1)
    run_dir.mkdir(parents=True, exist_ok=True)

    run = Run(
        id=run_index + 1,
        include_skill=evaluation.include_skill,
        response=response.message,
        tokens_input=response.tokens_input,
        tokens_output=response.tokens_output,
        tokens_cached=response.tokens_cached,
        duration_seconds=response.duration_seconds,
        assessment=None,
        skill_name=response.skill_name,
        success=response.success,
        error=response.error,
        files=[]
    )

    (run_dir / "response.md").write_text(response.message, encoding="utf-8")
    (run_dir / "stdout.txt").write_text(response.stdout_raw, encoding="utf-8")
    (run_dir / "stderr.txt").write_text(response.stderr_raw, encoding="utf-8")
    (run_dir / "meta.json").write_text(json.dumps({
        "skill_name":       response.skill_name,
        "success":          response.success,
        "error":            response.error,
        "returncode":       response.returncode,
        "include_skill":    evaluation.include_skill,
        "tokens_input":     response.tokens_input,
        "tokens_output":    response.tokens_output,
        "tokens_cached":    response.tokens_cached,
        "duration_seconds": response.duration_seconds,
    }, indent=2), encoding="utf-8")

    return evaluation, run, run_dir

def run_prompt_in_temp_dir(task: RunTask) -> tuple[Evaluation, Run]:
    config = task.config
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        shutil.copytree(config.github_dir, tmp_path / ".github")

        if not task.evaluation.include_skill:
            shutil.rmtree(tmp_path / ".github" / "skills" / config.skill_name)

        before = {f for f in tmp_path.rglob("*") if f.is_file()}

        evaluation, run, run_dir = run_prompt(task, cwd=tmp_path)

        after = {f for f in tmp_path.rglob("*") if f.is_file()}
        for f in after - before:
            dest = run_dir / f.relative_to(tmp_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
            run.files.append(dest)

        return evaluation, run

def get_split_evaluations(evaluations: list[Evaluation]) -> list[ExtEvaluation]:
    split_evaluations = []
    for evaluation in evaluations:
        include_skill_eval = ExtEvaluation(evaluation, True)
        exclude_skill_eval = ExtEvaluation(evaluation, False)
        split_evaluations.append(include_skill_eval)
        split_evaluations.append(exclude_skill_eval)

    return split_evaluations

def run_prompts(evaluations: list[Evaluation], iteration_dir: Path, config: EvaluationConfig) -> list[Evaluation]:
    """Run each evaluation multiple times concurrently."""
    split_evaluations = get_split_evaluations(evaluations)
    tasks = [
        RunTask(evaluation, run_num, config.times, iteration_dir, config)
        for evaluation in split_evaluations
        for run_num in range(config.times)
    ]
    
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(run_prompt_in_temp_dir, tasks))
    
    # Collect runs by evaluation ID
    evaluation_runs = {eval.id: [] for eval in evaluations}
    for evaluation, run in results:
        evaluation_runs[evaluation.id].append(run)
    
    # Update evaluations with their runs
    for evaluation in evaluations:
        evaluation.runs.extend(evaluation_runs[evaluation.id])
    
    return evaluations

def main():
    config = EvaluationConfig(skill_name="hello-user")
    eval_location = setup_eval_location(config)
    iteration_dir = get_results_dir(config)
    skill_eval = get_evals(config)
    evaluations = skill_eval.evaluations
    evaluations_with_runs = run_prompts(evaluations, iteration_dir, config)
    pprint([{"id": e.id, "runs_count": len(e.runs)} for e in evaluations_with_runs])
    updated_skill_eval = copy.deepcopy(skill_eval)
    updated_skill_eval.evaluations = evaluations_with_runs

    updated_skill_eval.to_json_file(eval_location)

main()