# `take_evaluation.py` Refactor Plan

## Problem Statement

`take_evaluation.py` has grown into a procedural script with a god-function (`run_prompt`),
global mutable state (`SKILL_NAME`), hardcoded configuration, and no seams for testing.
This plan applies SOLID principles to produce a modular, testable, extensible design.

---

## Target Architecture

```
scripts/
  take_evaluation.py        ← thin CLI entrypoint only
  evaluation_config.py      ← NEW: EvaluationConfig dataclass (replaces globals)
  command_runner.py         ← NEW: CopilotCommandRunner (abstracts subprocess)
  run_factory.py            ← NEW: builds Run objects from responses
  run_directory_writer.py   ← NEW: writes output files to disk
  evaluation_runner.py      ← NEW: orchestrates a single evaluation run
  evaluation_models.py      ← existing (minor fix)
  copilot_models.py         ← existing (add format_summary)
```

---

## Phases

---

### ✅ Phase 1 — Eliminate Global State (`EvaluationConfig`) — DONE

**Delivered:**

- `scripts/evaluation_config.py` — new `EvaluationConfig` dataclass; all path resolution in `__post_init__`; structural string constants exported
- `scripts/evaluation_models.py` — `RunTask` gains `config: EvaluationConfig`; `TYPE_CHECKING` import keeps runtime clean
- `scripts/take_evaluation.py` — all 11 module-level globals removed; `set_skill_name()` deleted; every function receives `config` explicitly; `model`/`allowed_tools` now driven by config; unbound method call fixed

**SOLID applied:** SRP, DIP

---

### Phase 2 — Abstract Command Execution (`CopilotCommandRunner`)

**File:** `scripts/command_runner.py`

**Problem:** `run_prompt` directly calls `subprocess.run`, making it impossible to unit-test
without actually invoking the CLI.

**Action:**

- Extract a `CopilotCommandRunner` class with a single `run(prompt: str, cwd: Path) -> CopilotResponse` method.
- Command construction (currently line 64) moves into `CopilotCommandRunner`, driven by config fields.
- In production, uses `subprocess.run`. In tests, can be replaced with a fake/mock.

```python
class CopilotCommandRunner:
    def __init__(self, config: EvaluationConfig): ...
    def run(self, prompt: str, cwd: Path) -> CopilotResponse: ...
```

**SOLID:** DIP (caller depends on runner abstraction, not subprocess directly), OCP (swap runner without touching callers)

---

### Phase 3 — Split `run_prompt` (SRP)

`run_prompt` (lines 57–125) does five distinct things. Each becomes its own unit.

#### 3a — `CopilotResponse.format_summary()`

**File:** `scripts/copilot_models.py`

The print block (lines 78–89) belongs on `CopilotResponse`, not in the runner.

```python
def format_summary(self, eval_id: int, run_index: int, total_runs: int, include_skill: bool) -> str:
    ...
```

#### 3b — `RunFactory`

**File:** `scripts/run_factory.py`

Building a `Run` dataclass (lines 95–108) from a `CopilotResponse` + `ExtEvaluation` is pure data transformation — no I/O.

```python
class RunFactory:
    @staticmethod
    def create(response: CopilotResponse, evaluation: ExtEvaluation, run_index: int) -> Run:
        ...
```

#### 3c — `RunDirectoryWriter`

**File:** `scripts/run_directory_writer.py`

Writing `response.md`, `stdout.txt`, `stderr.txt`, `meta.json` (lines 110–123) is I/O only.

```python
class RunDirectoryWriter:
    def write(self, run_dir: Path, response: CopilotResponse, evaluation: ExtEvaluation) -> None:
        ...
```

Named constants for all magic strings live here:

```python
RESPONSE_FILE = "response.md"
STDOUT_FILE   = "stdout.txt"
STDERR_FILE   = "stderr.txt"
META_FILE     = "meta.json"
WITH_SKILL    = "with_skill"
WITHOUT_SKILL = "without_skill"
```

#### 3d — `EvaluationRunner`

**File:** `scripts/evaluation_runner.py`

Thin orchestrator that wires together `CopilotCommandRunner`, `RunFactory`, and `RunDirectoryWriter`.
Replaces `run_prompt` and `run_prompt_in_temp_dir`.

```python
class EvaluationRunner:
    def __init__(self, config: EvaluationConfig, runner: CopilotCommandRunner,
                 factory: RunFactory, writer: RunDirectoryWriter): ...

    def run_task(self, task: RunTask) -> tuple[Evaluation, Run]: ...
```

**SOLID:** SRP (each class has one job), DIP (orchestrator depends on injected collaborators)

---

### Phase 4 — Minor Cleanups

These are quick, low-risk, standalone fixes.

| #   | Issue                                                                                          | Fix                                                     |
| --- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| 4a  | `main()` called at module level (line 196)                                                     | Wrap in `if __name__ == "__main__":`                    |
| 4b  | `skill_name` hardcoded as `"hello-user"` in `main()`                                           | Use `argparse` for `--skill-name`, `--model`, `--times` |
| 4c  | ~~`SkillEvaluation.to_json_file(updated_skill_eval, eval_location)` called as unbound method~~ | ✅ Fixed in Phase 1                                     |
| 4d  | `get_split_evaluations` can be a generator expression                                          | Simplify to list comprehension                          |
| 4e  | `parents[1]` / `parents[4]` magic indices                                                      | Name them via constants or move into `EvaluationConfig` |

---

## Execution Order

Dependencies flow top-to-bottom. Each phase can be reviewed independently.

```
Phase 1 (EvaluationConfig)
    └── Phase 2 (CopilotCommandRunner)  ← depends on config
            └── Phase 3a (format_summary)
            └── Phase 3b (RunFactory)
            └── Phase 3c (RunDirectoryWriter)
                    └── Phase 3d (EvaluationRunner)  ← wires 2 + 3a–c
Phase 4 (cleanups)  ← independent, can be done anytime
```

---

## Files Changed / Created

| File                              | Status                                                       |
| --------------------------------- | ------------------------------------------------------------ |
| `scripts/evaluation_config.py`    | ✅ Done                                                      |
| `scripts/evaluation_models.py`    | ✅ Done (`RunTask.config` + `TYPE_CHECKING` import)          |
| `scripts/take_evaluation.py`      | 🔄 In progress (globals removed; more changes in phases 3–4) |
| `scripts/command_runner.py`       | **New** — Phase 2                                            |
| `scripts/run_factory.py`          | **New** — Phase 3b                                           |
| `scripts/run_directory_writer.py` | **New** — Phase 3c                                           |
| `scripts/evaluation_runner.py`    | **New** — Phase 3d                                           |
| `scripts/copilot_models.py`       | Modified — Phase 3a (add `format_summary`)                   |
