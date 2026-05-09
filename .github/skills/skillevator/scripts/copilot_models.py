from dataclasses import dataclass
from typing import Optional
import re


@dataclass
class CopilotResponse:
    """Parsed response from a Copilot CLI command."""
    skill_name: Optional[str] = None
    success: bool = False
    message: str = ""
    error: Optional[str] = None
    stdout_raw: str = ""
    stderr_raw: str = ""
    returncode: int = 0
    tokens_input: Optional[str] = None
    tokens_output: Optional[str] = None
    tokens_cached: Optional[str] = None
    duration_seconds: Optional[float] = None

    @classmethod
    def from_subprocess_result(cls, result):
        """
        Parse a CompletedProcess result from subprocess.run() into a CopilotResponse.

        Args:
            result: subprocess.CompletedProcess object with stdout, stderr, returncode

        Returns:
            CopilotResponse with parsed fields
        """
        obj = cls(
            stdout_raw=result.stdout,
            stderr_raw=result.stderr,
            returncode=result.returncode
        )

        # Parse skill name (● skill(name))
        match = re.search(r'●\s*skill\(([^)]+)\)', result.stdout)
        obj.skill_name = match.group(1) if match else None

        # Check for success/failure
        obj.success = result.returncode == 0 and "✗" not in result.stdout

        # Extract error if present
        if "✗" in result.stdout:
            error_line = result.stdout.split("✗")[1].split("\n")[0].strip()
            obj.error = error_line

        # Get the main message (everything after skill name header)
        lines = result.stdout.split("\n")
        message_lines = [l for l in lines[2:] if l.strip()]
        obj.message = "\n".join(message_lines)

        # Parse tokens from stderr (Tokens    ↑ 96.2k • ↓ 109 • 13.3k (cached))
        tokens_match = re.search(r'Tokens\s+↑\s+([\d.]+k?)\s*•\s*↓\s+([\d.]+)\s*•\s+([\d.]+k?)', result.stderr)
        if tokens_match:
            obj.tokens_input = tokens_match.group(1)
            obj.tokens_output = tokens_match.group(2)
            obj.tokens_cached = tokens_match.group(3)

        # Parse duration from stderr (Requests  0 Premium (15s))
        duration_match = re.search(r'\((\d+(?:\.\d+)?)s\)', result.stderr)
        if duration_match:
            obj.duration_seconds = float(duration_match.group(1))

        return obj
