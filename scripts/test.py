import argparse
import json
import os
import subprocess
import shutil
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(".").resolve()
GITHUB = ".github"
SKILLS = "skills"
GITHUB_DIR = PROJECT_ROOT / GITHUB
SKILLS_DIR = PROJECT_ROOT / GITHUB / SKILLS

def print_tree(directory, prefix=""):
    """Recursively prints a visual directory tree."""
    path = Path(directory)
    # Get all items in the directory and sort them (directories first)
    items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
    
    for i, item in enumerate(items):
        is_last = (i == len(items) - 1)
        connector = "└── " if is_last else "├── "
        
        print(f"{prefix}{connector}{item.name}")
        
        if item.is_dir():
            # Extend the prefix for sub-items
            new_prefix = prefix + ("    " if is_last else "│   ")
            print_tree(item, new_prefix)

# Usage: Print the tree starting from the current directory

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

def run_eval(skill: str, prompts: list[str], include_skills: bool) -> list[dict]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        
        # Copy the .github dir (or just the parts Copilot needs)
        if include_skills:
            shutil.copytree(GITHUB_DIR, tmp_path / GITHUB)
        else:
            # Copy .github but omit skills/
            shutil.copytree(GITHUB_DIR, tmp_path / GITHUB,
                ignore=ignore_skill(skill)
            )
        
        print_tree(tmp_path)
        
        return _run_prompts(prompts, cwd=tmp_path, label=str(include_skills))

def _run_prompts(prompts, cwd, label) -> list[dict]:
    results = []
    for prompt in prompts:
        cmd = f'copilot --model gpt-4.1 -p "{prompt}"'
        result = subprocess.run(
            cmd,
            capture_output=True,
            cwd=cwd,
            env=os.environ,
            shell=True,
            encoding='utf-8',
            errors='replace'
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
        evals = data["evals"]

        prompts = [eval["prompt"] for eval in evals]
        print(prompts)
        return prompts

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
    prompts = get_prompts(skill_dir)
    with_skill = run_eval("hello-user", ["What skills do you have access to? Just list the names."], True)
    print("=============================================")
    print(json.dumps(with_skill[0], indent=2))
    print("=============================================")
    without_skill = run_eval("hello-user", ["What skills do you have access to? Just list the names."], False)
    print(json.dumps(without_skill[0], indent=2))
    print("=============================================")


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