# Skillevator: `take_evaluation.py` Implementation Plan

## Problem

The evaluation runner is partially built. Prompts fire and responses come back, but:

- The output directory is never created or used
- The temp dir cwd bug means the subprocess runs against the real project (defeating isolation)
- `include_skill=False` doesn't actually exclude the skill
- Responses and created files are never written to disk
- Several model fields are missing

## Approach

Fix bugs first (they unblock everything else), then layer in model changes, wiring, and output writing.

---

## Output File Structure (target)

```
evaluations/
  <skill_name>/
    iteration-01/
      <evaluation_name>/
        with_skill/
          1/
            response.md
            meta.json
            <any files created by copilot>
          2/ ...
          3/ ...
        without_skill/
          1/ ...
```

### `response.md`

The raw message text from `CopilotResponse.message`.

### `meta.json`

```json
{
  "skill_name": "hello-user",
  "success": true,
  "error": null,
  "returncode": 0,
  "include_skill": true,
  "tokens_input": "96.2k",
  "tokens_output": "109",
  "tokens_cached": "13.3k",
  "duration_seconds": 15.0
}
```

---

## Tasks

### Phase 1 — Bug Fixes ✅

**`model-fix-none-assessment`** ✅ — Fix null-assessment crash in `from_dict`  
`SkillEvaluation.from_dict` always calls `Assessment(**r["assessment"])` with no null check.
New runs always have `assessment: None`, so this crashes on reload.  
Fix: `assessment=Assessment(**r["assessment"]) if r.get("assessment") else None`

**`fix-cwd-bug`** ✅ — Fix cwd bug in `run_prompt`  
`run_prompt` hardcodes `cwd=str(PROJECT_ROOT)`, so the subprocess always runs against the
real project regardless of which temp dir was set up. Added `cwd: Path = PROJECT_ROOT`
parameter to `run_prompt`; `run_prompt_in_temp_dir` now passes `cwd=tmp_path`.

---

### Phase 2 — Data Model Changes ✅

**`model-eval-name`** ✅ — Add `evaluation_name` to `Evaluation`  
Added `evaluation_name: str` to `Evaluation` (after `id`), propagated in
`ExtEvaluation.__init__`, and added to `SkillEvaluation.from_dict`.

**`model-run-fields`** ✅ — Add `skill_name`, `success`, `error` to `Run`  
Added `skill_name: Optional[str] = None`, `success: Optional[bool] = None`,
`error: Optional[str] = None` to `Run` (with defaults, after required fields, before
`files`). Old serialized JSON without these keys safely falls back to `None` via the
`**r` spread in `from_dict`. `stdout_raw`, `stderr_raw`, `returncode` go to files only.

**`evals-json-eval-name`** ✅ _(depends on `model-eval-name`)_  
Added `evaluation_name` to all three entries in `hello-user/evals/evals.json`:
`"hello"`, `"hey-copilot"`, `"hello-copilot"`.

---

### Phase 3 — Wiring ✅

**`wire-results-dir`** ✅ — Wire up `get_results_dir()` in `main()`  
Called `get_results_dir()` in `main()` to create the versioned `iteration-NN` directory.
`iteration_dir` is now passed into `run_prompts` as an explicit parameter and flows
through to every `RunTask`.

**`args-tuple-refactor`** ✅ _(depends on `wire-results-dir`)_  
Added `RunTask` dataclass to `evaluation_models.py` (after `ExtEvaluation`):

```python
@dataclass
class RunTask:
    evaluation: ExtEvaluation
    run_index: int
    total_runs: int
    iteration_dir: Path
```

Replaced the `(evaluation, run_num, times)` tuple throughout:

- `run_prompts` builds `RunTask(evaluation, run_num, times, iteration_dir)`
- `run_prompt_in_temp_dir(task: RunTask)` unpacks via attribute access
- `run_prompt(task: RunTask, cwd)` unpacks `task.evaluation / .run_index / .total_runs`

---

### Phase 4 — Conditional Copy & File Capture

**`conditional-copy`** _(depends on `fix-cwd-bug`)_  
In `run_prompt_in_temp_dir`, when `include_skill=False`, after copying `.github/` into
the temp dir, call `shutil.rmtree(tmp_path / GITHUB / SKILLS / SKILL_NAME)` to remove
the skill directory. The subprocess will then run as if the skill doesn't exist.

**`snapshot-temp-dir`**  
Before calling `run_prompt`, record the set of all file paths currently in the temp dir.
After the run completes, diff the before/after sets to find newly created files.
Return the list of new paths alongside `(evaluation, run)`.

**`copy-created-files`** _(depends on `snapshot-temp-dir`, `output-dir-structure`)_  
Copy each newly created file from the temp dir into the `<run_num>/` output directory,
preserving relative paths. Populate `Run.files` with the destination paths.

---

### Phase 5 — Output File Writing

**`output-dir-structure`** _(depends on `args-tuple-refactor`, `model-eval-name`, `wire-results-dir`)_  
In `run_prompt`, resolve and create the output directory:

```
<iteration_dir>/<evaluation_name>/<with_skill|without_skill>/<run_num>/
```

Use `"with_skill"` and `"without_skill"` as the literal folder names.

**`write-response-file`** _(depends on `model-run-fields`, `output-dir-structure`)_  
After each run, write four files into `<run_num>/`:

- `response.md` — `CopilotResponse.message` (processed output only)
- `meta.json` — `skill_name`, `success`, `error`, `returncode`, `include_skill`,
  `tokens_input`, `tokens_output`, `tokens_cached`, `duration_seconds`
- `stdout.txt` — `CopilotResponse.stdout_raw`
- `stderr.txt` — `CopilotResponse.stderr_raw` (contains token/timing lines)

Raw output goes to plain text files rather than into `meta.json` to keep the JSON
clean and machine-readable. Plain text is also easier to inspect when debugging a run.

---

## Dependency Graph

```
model-fix-none-assessment   ✅
fix-cwd-bug                 ✅
  └─ conditional-copy

model-eval-name             ✅
  └─ evals-json-eval-name  ✅
  └─ output-dir-structure

model-run-fields            ✅
  └─ write-response-file

wire-results-dir            ✅
  └─ args-tuple-refactor   ✅
       └─ output-dir-structure
            └─ write-response-file
            └─ copy-created-files

snapshot-temp-dir           (no deps)
  └─ copy-created-files
```
