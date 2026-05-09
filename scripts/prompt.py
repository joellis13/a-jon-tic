import os
import subprocess


def run_prompt(prompt):
    cmd = f'copilot --model claude-haiku-4.5 --yolo -p "{prompt}"'
    result = subprocess.run(
        cmd,
        capture_output=True,
        env=os.environ,
        shell=True,
        encoding='utf-8',
        errors='replace'
    )

    print("==========================================")
    print("Result: " + str(result))
    print("==========================================")
    print("Result Type: " + str(type(result)))
    print("==========================================")
    print("Response: " + result.stdout)
    print("==========================================")
    print("Error: " + result.stderr)
    print("==========================================")
    print("Return Code: " + str(result.returncode))
    print("==========================================")

def main():
    prompt = """
    Hello
    """

    run_prompt(prompt)

main()