from pathlib import Path
import subprocess

from evaluation_config import EvaluationConfig
from copilot_models import CopilotResponse


class CopilotCommandRunner:
    """Builds and executes the copilot CLI command, returning a parsed CopilotResponse.

    Abstracting subprocess here creates a seam for testing: swap this class for a
    fake that returns canned CopilotResponse objects without touching the network.
    """

    def __init__(self, config: EvaluationConfig) -> None:
        self._config = config

    def build_command(self, prompt: str) -> str:
        return (
            f"copilot --allow-tool=\"{self._config.allowed_tools}\""
            f" --model {self._config.model}"
            f" -p \"{prompt}\""
        )

    def run(self, prompt: str, cwd: Path) -> CopilotResponse:
        result = subprocess.run(
            self.build_command(prompt),
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(cwd),
        )
        return CopilotResponse.from_subprocess_result(result)
