import os
import shutil
import subprocess
import sys
from pathlib import Path

from evaluation_config import EvaluationConfig
from copilot_models import CopilotResponse


def _find_copilot_loader() -> str | None:
    """Return the path to copilot's npm-loader.js, or None if not found.

    On Windows, copilot ships as a .cmd/.ps1 wrapper around a Node.js entry
    point.  Calling the wrapper via CreateProcess (shell=False) is fragile —
    the .cmd → cmd.exe chain mangles multiline arguments.  Calling node
    directly with the loader path sidesteps the wrapper entirely.
    """
    for name in ("copilot.cmd", "copilot.ps1", "copilot"):
        script = shutil.which(name)
        if script:
            loader = os.path.join(
                os.path.dirname(script),
                "node_modules", "@github", "copilot", "npm-loader.js",
            )
            if os.path.exists(loader):
                return loader
    return None


# Cached at import time so discovery runs only once per process.
_COPILOT_LOADER: str | None = _find_copilot_loader() if sys.platform == "win32" else None


class CopilotCommandRunner:
    """Builds and executes the copilot CLI command, returning a parsed CopilotResponse.

    Abstracting subprocess here creates a seam for testing: swap this class for a
    fake that returns canned CopilotResponse objects without touching the network.

    Prompt passing strategy
    -----------------------
    On Unix/macOS, ``shell=False`` + list argv passes any string (including
    multiline) safely as a single process argument.

    On Windows, copilot's .cmd/.ps1 wrappers route through cmd.exe or PowerShell,
    both of which mangle newlines in arguments.  To avoid this, we call
    ``node <npm-loader.js>`` directly — node.exe is a real executable that
    CreateProcess can call with ``shell=False``, and the prompt string is
    passed as a single list element with no shell interpretation.
    """

    def __init__(self, config: EvaluationConfig) -> None:
        self._config = config

    def build_command(self, prompt: str) -> list[str]:
        if sys.platform == "win32" and _COPILOT_LOADER:
            # Call node + npm-loader.js directly to avoid .cmd wrapper issues.
            parts = ["node", _COPILOT_LOADER]
        else:
            parts = ["copilot"]

        for t in self._config.allowed_tools:
            parts.append(f"--allow-tool={t}")
        parts.extend(["--model", self._config.model, "-p", prompt])
        return parts

    def run(self, prompt: str, cwd: Path) -> CopilotResponse:
        try:
            result = subprocess.run(
                self.build_command(prompt),
                shell=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=str(cwd),
                timeout=self._config.timeout,
            )
            return CopilotResponse.from_subprocess_result(result)
        except subprocess.TimeoutExpired:
            return CopilotResponse(
                success=False,
                returncode=-1,
                error=f"timeout after {self._config.timeout}s",
            )
