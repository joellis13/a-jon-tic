import asyncio
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime

@dataclass
class Run:
    prompt_id: str
    prompt: str
    condition: str        # "with_skill" | "without_skill"
    repetition: int       # 1, 2, 3
    stdout: str = ""
    stderr: str = ""
    returncode: int = -1
    duration_s: float = 0.0

async def execute_run(run: Run, semaphore: asyncio.Semaphore) -> Run:
    cmd = ["copilot", "--model", "gpt-5.2", "-p", run.prompt]
    
    if run.condition == "with_skill":
        cmd += ["--skill", "path/to/skill"]  # adjust to your CLI flags

    async with semaphore:
        start = asyncio.get_event_loop().time()
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        elapsed = asyncio.get_event_loop().time() - start

    run.stdout = stdout.decode()
    run.stderr = stderr.decode()
    run.returncode = proc.returncode or -1
    run.duration_s = round(elapsed, 2)
    return run

def build_runs(prompts: dict[str, str], repetitions: int = 3) -> list[Run]:
    """Expand prompts into the full run matrix."""
    runs = []
    for prompt_id, prompt in prompts.items():
        for condition in ("with_skill", "without_skill"):
            for rep in range(1, repetitions + 1):
                runs.append(Run(
                    prompt_id=prompt_id,
                    prompt=prompt,
                    condition=condition,
                    repetition=rep,
                ))
    return runs

def save_run(run: Run, output_dir: Path) -> None:
    run_dir = output_dir / run.prompt_id
    run_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{run.condition}_{run.repetition}.json"
    (run_dir / filename).write_text(json.dumps(asdict(run), indent=2))

async def main():
    output_dir = Path("runs") / datetime.now().strftime("%Y%m%d_%H%M%S")
    prompts = {
        "prompt_001": "Refactor the auth module to use dependency injection",
        "prompt_002": "Add error handling to the API client",
        # ...
    }

    runs = build_runs(prompts, repetitions=3)
    semaphore = asyncio.Semaphore(6)  # tune to avoid rate limits

    print(f"Executing {len(runs)} runs ({len(prompts)} prompts × 6 variants)...")

    tasks = [execute_run(r, semaphore) for r in runs]
    completed = await asyncio.gather(*tasks)

    for run in completed:
        save_run(run, output_dir)

    # Quick summary
    failures = [r for r in completed if r.returncode != 0]
    print(f"\nDone. {len(completed) - len(failures)}/{len(completed)} succeeded.")
    if failures:
        print(f"Failed runs: {[f'{f.prompt_id}/{f.condition}/{f.repetition}' for f in failures]}")

asyncio.run(main())