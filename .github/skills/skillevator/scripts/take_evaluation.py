
from concurrent.futures import ThreadPoolExecutor
import copy
from pprint import pprint
from pathlib import Path
import shutil
import subprocess
import tempfile

from evaluation_models import ExtEvaluation, SkillEvaluation, Evaluation, Run, RunTask
from copilot_models import CopilotResponse

SKILL_NAME = ""
SKILL_EVAL_RESULTS_DIR = ""
CURRENT_WORKING_DIR = Path(__file__).resolve()
SKILLEVATOR_ROOT = CURRENT_WORKING_DIR.parents[1]
PROJECT_ROOT = CURRENT_WORKING_DIR.parents[4]
GITHUB = ".github"
SKILLS = "skills"
GITHUB_DIR = PROJECT_ROOT / GITHUB
SKILLS_DIR = PROJECT_ROOT / GITHUB / SKILLS
EVALS = "evals"
EVALUATIONS = "evaluations"
EVALS_JSON = "evals.json"
SKILLEVATOR_EVALUATIONS = SKILLEVATOR_ROOT / EVALUATIONS

def set_skill_name(skill_name: str):
    global SKILL_NAME
    SKILL_NAME = skill_name

def get_results_dir() -> Path:
    skill_eval_dir = SKILLEVATOR_EVALUATIONS / SKILL_NAME
    base_name = skill_eval_dir / "iteration"
    counter = 1
    while True:
        directory_name = Path(f"{base_name}-{counter:02d}")
        if not directory_name.exists():
            directory_name.mkdir(parents=True)
            print(f"Created: {directory_name}")
            return directory_name
        counter += 1

def setup_eval_location() -> Path:
    skill_evaluation_directory = SKILLEVATOR_EVALUATIONS / SKILL_NAME
    skill_evaluation_directory.mkdir(parents=True, exist_ok=True)
    return skill_evaluation_directory / EVALS_JSON

def get_evals() -> SkillEvaluation :
    skill_dir = SKILLS_DIR / SKILL_NAME
    skill_eval_file = skill_dir / EVALS / EVALS_JSON 

    skill_eval = SkillEvaluation.from_json_file(skill_eval_file)

    return skill_eval

def run_prompt(task: RunTask, cwd: Path = PROJECT_ROOT) -> tuple[Evaluation, Run]:
    """Run a single prompt and return the evaluation + run result."""
    evaluation = task.evaluation
    run_index = task.run_index
    total_runs = task.total_runs
    eval_id = evaluation.id
    prompt = evaluation.prompt
    command = "copilot --allow-tool=\"shell(python)\" --model gpt-4.1 -p \"" + prompt + "\""
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
    
    run = Run(
        id=run_index + 1,
        include_skill=evaluation.include_skill,
        response=response.message,
        tokens_input=response.tokens_input,
        tokens_output=response.tokens_output,
        tokens_cached=response.tokens_cached,
        duration_seconds=response.duration_seconds,
        assessment=None,
        files=[]
    )
    
    return evaluation, run

def run_prompt_in_temp_dir(task: RunTask) -> tuple[Evaluation, Run]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        shutil.copytree(GITHUB_DIR, tmp_path / GITHUB)

        return run_prompt(task, cwd=tmp_path)

def get_split_evaluations(evaluations: list[Evaluation]) -> list[ExtEvaluation]:
    split_evaluations = []
    for evaluation in evaluations:
        include_skill_eval = ExtEvaluation(evaluation, True)
        exclude_skill_eval = ExtEvaluation(evaluation, False)
        split_evaluations.append(include_skill_eval)
        split_evaluations.append(exclude_skill_eval)

    return split_evaluations

def run_prompts(evaluations: list[Evaluation], iteration_dir: Path, times: int = 3) -> list[Evaluation]:
    """Run each evaluation multiple times concurrently."""
    split_evaluations = get_split_evaluations(evaluations)
    # Create tasks: RunTask for each evaluation × times
    tasks = [
        RunTask(evaluation, run_num, times, iteration_dir)
        for evaluation in split_evaluations
        for run_num in range(times)
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
    skill_name = "hello-user"
    set_skill_name(skill_name)
    eval_location = setup_eval_location()
    iteration_dir = get_results_dir()
    skill_eval = get_evals()
    evaluations = skill_eval.evaluations
    evaluations_with_runs = run_prompts(evaluations, iteration_dir, times=3)
    pprint([{"id": e.id, "runs_count": len(e.runs)} for e in evaluations_with_runs])
    updated_skill_eval = copy.deepcopy(skill_eval)
    updated_skill_eval.evaluations = evaluations_with_runs

    SkillEvaluation.to_json_file(updated_skill_eval, eval_location)

main()