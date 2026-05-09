
from concurrent.futures import ThreadPoolExecutor
import copy
from pprint import pprint
from pathlib import Path
import shutil
import subprocess
import tempfile

from evaluation_models import SkillEvaluation, Evaluation, Run
from copilot_models import CopilotResponse

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

def setup_eval_location(skill_name: str) -> Path:
    skill_evaluation_directory = SKILLEVATOR_EVALUATIONS / skill_name
    skill_evaluation_directory.mkdir(parents=True, exist_ok=True)
    return skill_evaluation_directory / EVALS_JSON

def get_evals(skill_name: str) -> SkillEvaluation :
    skill_dir = SKILLS_DIR / skill_name
    skill_eval_file = skill_dir / EVALS / EVALS_JSON 

    skill_eval = SkillEvaluation.from_json_file(skill_eval_file)

    return skill_eval

def run_prompt(args: tuple[Evaluation, int, int, Path, bool, int]) -> tuple[Evaluation, Run]:
    """Run a single prompt and return the evaluation + run result."""
    evaluation, run_index, total_runs, cwd, include_skills, run_id_offset = args
    eval_id = evaluation.id
    prompt = evaluation.prompt
    command = [
        "copilot",
        "--allow-tool=shell(python)",
        "--model",
        "gpt-4.1",
        "-p",
        prompt,
    ]
    print(f"[Run {run_index + 1}/{total_runs}] command {eval_id}: {command}")

    result = subprocess.run(
        command,
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
    print("message: " + str(response.message))
    print("tokens_input: " + str(response.tokens_input))
    print("duration_seconds: " + str(response.duration_seconds))
    print("include_skills: " + str(include_skills))
    print("==================================================\n")
    
    run = Run(
        id=run_id_offset + run_index + 1,
        response=response.message,
        tokens_input=response.tokens_input,
        tokens_output=response.tokens_output,
        tokens_cached=response.tokens_cached,
        duration_seconds=response.duration_seconds,
        assessment=None,
        include_skills=include_skills,
        files=[]
    )
    
    return evaluation, run

def run_prompts(
    evaluations: list[Evaluation],
    cwd: Path,
    include_skills: bool,
    times: int = 3,
    run_id_offset: int = 0,
) -> list[Evaluation]:
    """Run each evaluation multiple times concurrently."""
    # Create tasks: (evaluation, run_index, total_runs, cwd, include_skills, run_id_offset)
    tasks = [
        (evaluation, run_num, times, cwd, include_skills, run_id_offset)
        for evaluation in evaluations
        for run_num in range(times)
    ]
    
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(run_prompt, tasks))
    
    # Collect runs by evaluation ID
    evaluation_runs = {eval.id: [] for eval in evaluations}
    for evaluation, run in results:
        evaluation_runs[evaluation.id].append(run)
    
    # Update evaluations with their runs
    for evaluation in evaluations:
        evaluation.runs.extend(evaluation_runs[evaluation.id])
    
    return evaluations

def ignore_skill(skill: str):
    """Returns an ignore function for a specific skill directory."""
    def _ignore(directory, files):
        result = []
        # Check if we're currently in the skills directory
        if directory.endswith("skills"):
            # Ignore just the specific skill subdirectory
            if skill in files:
                result.append(skill)
        return result
    return _ignore

def run_prompts_in_temp_dir(
    evaluations: list[Evaluation],
    skill_name: str,
    include_skills: bool,
    times: int = 3,
    run_id_offset: int = 0,
) -> list[Evaluation]:
    
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        
        # Copy the .github dir (or just the parts Copilot needs)
        if include_skills:
            shutil.copytree(GITHUB_DIR, tmp_path / GITHUB)
        else:
            # Copy .github but omit skills/
            shutil.copytree(GITHUB_DIR, tmp_path / GITHUB,
                ignore=ignore_skill(skill_name)
            )

        return run_prompts(
            evaluations,
            cwd=tmp_path,
            include_skills=include_skills,
            times=times,
            run_id_offset=run_id_offset,
        )


def run_with_and_without_skills(
    evaluations: list[Evaluation],
    skill_name: str,
    times: int = 3,
) -> list[Evaluation]:
    evaluations = run_prompts_in_temp_dir(
        evaluations,
        skill_name=skill_name,
        include_skills=True,
        times=times,
        run_id_offset=0,
    )
    evaluations = run_prompts_in_temp_dir(
        evaluations,
        skill_name=skill_name,
        include_skills=False,
        times=times,
        run_id_offset=times,
    )
    return evaluations


def main():
    skill_name = "hello-user"
    eval_location = setup_eval_location(skill_name)
    skill_eval = get_evals(skill_name)
    evaluations = skill_eval.evaluations
    evaluations_with_runs = run_with_and_without_skills(
        evaluations,
        skill_name=skill_name,
        times=3,
    )
    pprint([{"id": e.id, "runs_count": len(e.runs)} for e in evaluations_with_runs])
    updated_skill_eval = copy.deepcopy(skill_eval)
    updated_skill_eval.evaluations = evaluations_with_runs

    updated_skill_eval.to_json_file(eval_location)


if __name__ == "__main__":
    main()