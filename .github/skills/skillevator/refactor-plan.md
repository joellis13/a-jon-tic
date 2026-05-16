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

### ✅ Phase 2 — Abstract Command Execution (`CopilotCommandRunner`) — DONE

**Delivered:**

- `scripts/command_runner.py` — new `CopilotCommandRunner`; `build_command(prompt)` for logging, `run(prompt, cwd) -> CopilotResponse` for execution; `subprocess` lives here only
- `scripts/take_evaluation.py` — `import subprocess` removed; `run_prompt` creates `CopilotCommandRunner(task.config)` and delegates to it; log line uses `runner.build_command()`

**Note:** `run_prompt` still instantiates the runner itself — Phase 3d's `EvaluationRunner` will receive it as an injected dependency, completing DIP.

**SOLID applied:** DIP, OCP

---

### ✅ Phase 3 — Split `run_prompt` (SRP) — DONE

**Delivered:**

- `scripts/copilot_models.py` — `CopilotResponse.format_summary(eval_id, run_index, total_runs, include_skill) -> str`; replaces inline print block
- `scripts/run_factory.py` — new `RunFactory.create(response, evaluation, run_index) -> Run`; pure data transformation, no I/O
- `scripts/run_directory_writer.py` — new `RunDirectoryWriter.write(run_dir, response, evaluation)`; pure I/O; named constants `RESPONSE_FILE`, `STDOUT_FILE`, `STDERR_FILE`, `META_FILE`, `WITH_SKILL`, `WITHOUT_SKILL`
- `scripts/evaluation_runner.py` — new `EvaluationRunner(config, runner, factory, writer)`; `run_task(task) -> tuple[Evaluation, Run]`; replaces `run_prompt` + `run_prompt_in_temp_dir`; all collaborators injected (DIP complete)
- `scripts/take_evaluation.py` — removed `run_prompt`, `run_prompt_in_temp_dir`; removed `json`, `shutil`, `tempfile`, `CopilotResponse`, `Run` imports; `run_prompts` now accepts `EvaluationRunner`; `main()` wires all dependencies; `get_split_evaluations` simplified

**SOLID applied:** SRP (each class has one job), DIP (EvaluationRunner receives all collaborators)

---

### ✅ Phase 4 — Minor Cleanups — DONE

**Delivered:**

| #   | Issue                                                              | Fix                                                                       |
| --- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| 4a  | `main()` called at module level                                    | ✅ Wrapped in `if __name__ == "__main__":`                                |
| 4b  | `skill_name` hardcoded as `"hello-user"` in `main()`              | ✅ `parse_args()` with `--skill-name`, `--model`, `--times` via argparse  |
| 4c  | ~~Unbound method call~~                                            | ✅ Fixed in Phase 1                                                       |
| 4d  | `get_split_evaluations` used a manual loop                         | ✅ Simplified to one-line list comprehension                              |
| 4e  | `parents[1]` / `parents[4]` magic indices in `evaluation_config`  | ✅ Replaced with `.parent.parent` chains with inline comments             |

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
| `scripts/take_evaluation.py`      | ✅ Done (thin CLI entrypoint; all phases complete)          |
| `scripts/command_runner.py`       | ✅ Done                                                      |
| `scripts/copilot_models.py`       | ✅ Done (`format_summary` added)                             |
| `scripts/run_factory.py`          | ✅ Done                                                      |
| `scripts/run_directory_writer.py` | ✅ Done                                                      |
| `scripts/evaluation_runner.py`    | ✅ Done                                                      |
