import json
from pathlib import Path

from copilot_models import CopilotResponse
from evaluation_models import ExtEvaluation

RESPONSE_FILE = "response.md"
STDOUT_FILE   = "stdout.txt"
STDERR_FILE   = "stderr.txt"
META_FILE     = "meta.json"
WITH_SKILL    = "with_skill"
BASELINE      = "baseline"


class RunDirectoryWriter:
    """Writes the output files for a single evaluation run to disk.

    Pure I/O — no business logic. Swap or subclass to vary serialization format.
    """

    def write(self, run_dir: Path, response: CopilotResponse, evaluation: ExtEvaluation, model: str, allowed_tools: list[str]) -> None:
        (run_dir / RESPONSE_FILE).write_text(response.stdout_raw, encoding="utf-8")
        (run_dir / STDOUT_FILE).write_text(response.stdout_raw, encoding="utf-8")
        (run_dir / STDERR_FILE).write_text(response.stderr_raw, encoding="utf-8")
        (run_dir / META_FILE).write_text(json.dumps({
            "model":            model,
            "prompt":           evaluation.prompt,
            "allowed_tools":    allowed_tools,
            "skill_name":       response.skill_name,
            "skill_triggered":  response.skill_name is not None,
            "success":          response.success,
            "error":            response.error,
            "returncode":       response.returncode,
            "include_skill":    evaluation.include_skill,
            "tokens_input":     response.tokens_input,
            "tokens_output":    response.tokens_output,
            "tokens_cached":    response.tokens_cached,
            "duration_seconds": response.duration_seconds,
        }, indent=2, ensure_ascii=False), encoding="utf-8")
