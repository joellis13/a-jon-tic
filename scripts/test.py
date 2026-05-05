import argparse
import json
import subprocess
import shutil
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(".").resolve()
GITHUB = ".github"
SKILLS = "skills"
SKILLS_DIR = PROJECT_ROOT / GITHUB / SKILLS

def run_eval(prompts: list[str], include_skills: bool) -> list[dict]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        
        # Copy the .github dir (or just the parts Copilot needs)
        if include_skills:
            shutil.copytree(PROJECT_ROOT / ".github", tmp_path / ".github")
        # else:
        #     # Copy .github but omit skills/
        #     shutil.copytree(
        #         PROJECT_ROOT / ".github",
        #         tmp_path / ".github",
        #         ignore=shutil.ignore_patterns("skills")
        #     )
        
        return _run_prompts(prompts, cwd=tmp_path, label=str(include_skills))

def _run_prompts(prompts, cwd, label) -> list[dict]:
    results = []
    for prompt in prompts:
        result = subprocess.run(
            ["copilot", "-p", prompt],
            capture_output=True, text=True,
            cwd=cwd
        )
        results.append({
            "label": label,
            "prompt": prompt,
            "response": result.stdout,
            "error": result.stderr,
        })
    return results

def get_prompts(skill_dir: Path):
    with open(skill_dir / "evals" / 'evals.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
        print(json.dumps(data["evals"], indent=2))
        return data["evals"]

def execute_run(args: argparse.Namespace):
    skill = args.skill_name
    include_skill = args.include_skill
    print("skill: " + str(skill))
    print("include_skill: " + str(include_skill))

    

    skill_dir = SKILLS_DIR / skill

    prompts = ["What skills do you have access to? Response with just a list of skill names"]

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        
        # print("### skill_dir: " + str(skill_dir))
        # print("tmp_path: " + str(tmp_path))
        # Copy the .github dir (or just the parts Copilot needs)
        if include_skill:
            print("copying skill")
            shutil.copytree(skill_dir, tmp_path / ".github" / "skills")
        else:
            print("NOT copying skill")
            # Copy .github but omit skills/
            # shutil.copytree(
            #     PROJECT_ROOT / ".github",
            #     tmp_path / ".github",
            #     ignore=shutil.ignore_patterns("skills")
            # )
        
        return _run_prompts(prompts, cwd=tmp_path, label=str(include_skill))



def setup_data(args: argparse.Namespace):
    skill = args.skill_name
    skill_dir = SKILLS_DIR / skill
    evaluations = get_prompts(skill_dir)

def main():
    parser = argparse.ArgumentParser(description="Test Copilot with and without skills.")
    parser.add_argument("--skill-name", type=str, required=True, help="Name of the skill to test (should be a subdir in .github/skills)")
    parser.add_argument("--include-skill", action='store_true', help="Include skills in the test")
    # parser.add_argument("--include-environment", type=bool, required=True, help="Include remaining copilot artifacts")
    # parser.add_argument("--model", type=str, required=True, help="Model for improvement")
    args = parser.parse_args()

    setup_data(args)
    # print(response[0]["response"])

    # pretty_response = json.dumps(response, indent=2)
    # print(pretty_response[0])


main()