import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))

from ..common.copilot_models import CopilotResponse
from ..common.evaluation_models import ExtEvaluation, Run


class RunFactory:
    """Builds a Run dataclass from a CopilotResponse and evaluation metadata.

    Pure data transformation — no I/O. Swap or subclass to vary Run construction.
    """

    @staticmethod
    def create(response: CopilotResponse, evaluation: ExtEvaluation, run_index: int, changes: dict) -> Run:
        return Run(
            id=run_index + 1,
            include_skill=evaluation.include_skill,
            response=response.stdout_raw,
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            tokens_cached=response.tokens_cached,
            duration_seconds=response.duration_seconds,
            assessment=None,
            skill_name=response.skill_name,
            skill_triggered=response.skill_name is not None,
            success=response.success,
            error=response.error,
            changes=changes,
        )
