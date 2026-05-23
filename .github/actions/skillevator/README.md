# skillevator

Runs a skill's evaluations against the Copilot CLI, records the results, and
assesses each run using the Copilot CLI as an LLM judge.

## Usage

### Locally (run from the **repository root**)

**Step 1 — Take evaluations** (runs the skill prompts, writes `evals.json`):

```bash
# Minimal (no tools, hello-user skill, default model)
python .github/actions/skillevator/scripts/take_evaluation.py

# Typical — specify skill and allow a tool
python .github/actions/skillevator/scripts/take_evaluation.py --skill-name hello-user --allow-tool "shell(python)"

# Full options
python .github/actions/skillevator/scripts/take_evaluation.py --skill-name hello-user --allow-tool "shell(python)" --model gpt-4.1 --times 3 --timeout 120
```

Pass `--allow-tool` once per tool. It mirrors the Copilot CLI flag directly.

```bash
# Multiple tools
python .github/actions/skillevator/scripts/take_evaluation.py --skill-name my-skill --allow-tool "shell(python)" --allow-tool "builtin"
```

**Step 2 — Assess evaluations** (grades each run, writes `assessment_summary.json`):

```bash
# Minimal
python .github/actions/skillevator/scripts/assess_evaluation.py

# Typical
python .github/actions/skillevator/scripts/assess_evaluation.py --skill-name hello-user --model gpt-4.1

# Re-grade runs that already have an assessment
python .github/actions/skillevator/scripts/assess_evaluation.py --skill-name hello-user --force
```

### In CI (GitHub Actions)

Both steps run automatically — the action runs the taker then the grader:

```yaml
- uses: ./.github/actions/skillevator
  with:
    skill-name: hello-user
    model: gpt-4.1
    times: 3
    timeout: 120
    allowed-tools: "shell(python) builtin"
```

| Flag           | Required | Default      | Description                                              |
| -------------- | -------- | ------------ | -------------------------------------------------------- |
| `--allow-tool` | no       | _(none)_     | Tool to allow; repeat for multiple (mirrors Copilot CLI) |
| `--skill-name` | no       | `hello-user` | Skill directory name under `.github/skills/`             |
| `--model`      | no       | `gpt-4.1`    | Copilot model passed to `--model`                        |
| `--times`      | no       | `3`          | Number of runs per evaluation prompt (taker only)        |
| `--timeout`    | no       | `120`        | Seconds before a taker CLI call is killed                |

The grader's timeout is fixed at 60 s (grading calls return short JSON, no tool use).

## Pipeline

```text
evals.json (skill definition)
        │
        ▼
take_evaluation.py          ← Step 1: run skill prompts
│   → evaluations/<skill>/iteration-NN/   (run dirs with response.md, meta.json, …)
│   → evaluations/<skill>/evals.json      (runs appended; assessment: null)
│
▼
assess_evaluation.py          ← Step 2: grade each run independently
    → evaluations/<skill>/evals.json              (assessment fields populated)
    → evaluations/<skill>/assessment_summary.json (pass rates, delta, per-criterion stats)
```

## Execution Order

### Taker (`take_evaluation.py`)

```text
take_evaluation.py
│
├── parse_args()            ← resolve --skill-name / --allow-tool / --model / --times / --timeout
├── EvaluationConfig        ← derive all paths from __file__ location
│
├── CopilotCommandRunner    ← wraps subprocess; receives config
├── RunFactory              ← builds Run dataclass from a response
├── RunDirectoryWriter      ← writes response.md / stdout.txt / stderr.txt / meta.json
└── EvaluationRunner        ← wires the above three; receives all via constructor
    │
    ├── setup_eval_location()   ← ensure evaluations/<skill>/ exists
    ├── get_results_dir()       ← create evaluations/<skill>/iteration-NN/
    ├── get_evals()             ← load evals.json from the skill's evals/ folder
    │
    └── run_prompts()           ← ThreadPoolExecutor over all tasks
        │
        ├── get_split_evaluations()     ← duplicate each eval: with_skill + baseline
        │
        └── EvaluationRunner.run_task() ← per task (runs concurrently)
            ├── copy .github/ into a temp dir
            ├── optionally remove the skill folder (baseline variant)
            ├── CopilotCommandRunner.run()      → CopilotResponse
            ├── CopilotResponse.format_summary()  → print progress
            ├── RunFactory.create()             → Run
            ├── RunDirectoryWriter.write()      → files on disk
            └── collect new files → Run.files
```

After all tasks complete, results are aggregated back into the `SkillEvaluation`
and written to `evaluations/<skill>/evals.json`.

### Grader (`assess_evaluation.py`)

```text
assess_evaluation.py
│
├── parse_args()            ← resolve --skill-name / --model / --timeout / --force
├── EvaluationConfig        ← reused from taker; same path resolution
│
└── AssessmentRunner        ← ThreadPoolExecutor over AssessmentTask list
    │
    └── AssessmentRunner.run_task() ← per task (runs concurrently)
        ├── grading_prompt_builder.build_grading_prompt()  → prompt string
        ├── CopilotCommandRunner.run() in a skill-absent temp dir → CopilotResponse
        └── assessment_parser.parse_assessment()           → Assessment
            ├── strip markdown fences
            ├── json.loads()
            ├── validate shape; fill missing criteria
            └── graceful degradation → passed=False with evidence on any parse error
```

After all tasks complete, `evals.json` is written once (single atomic write), then
`assessment_summary_writer.write_summary()` computes and writes `assessment_summary.json`.

## Assessment Output

Each `Run` in `evals.json` gains an `assessment` block:

````json
{
  "passed": true,
  "criteria_results": [
    {
      "id": 1,
      "criterion": "Output is wrapped in a fenced code block",
      "passed": true,
      "evidence": "The response begins with ```"
    }
  ]
}
````

`assessment.passed` is always derived (`all(criteria_results[i].passed)`) — never
assigned by the LLM.

`assessment_summary.json` rolls up pass rates, standard deviations, per-criterion
pass rates, and the with-skill vs. baseline delta across all evaluations.

## Module Map

| File                           | Responsibility                                                       |
| ------------------------------ | -------------------------------------------------------------------- |
| `take_evaluation.py`           | Taker CLI entrypoint; wires dependencies; orchestrates runs          |
| `assess_evaluation.py`         | Grader CLI entrypoint; wires dependencies; orchestrates grading      |
| `evaluation_config.py`         | `EvaluationConfig` dataclass; all path resolution                    |
| `command_runner.py`            | `CopilotCommandRunner`; owns `subprocess`                            |
| `copilot_models.py`            | `CopilotResponse`; parses CLI stdout/stderr                          |
| `run_factory.py`               | `RunFactory`; builds `Run` from response — no I/O                    |
| `run_directory_writer.py`      | `RunDirectoryWriter`; writes output files — no logic                 |
| `evaluation_runner.py`         | `EvaluationRunner`; per-task taker orchestrator                      |
| `grading_prompt_builder.py`    | Builds grading prompt string — pure function, no I/O                 |
| `assessment_parser.py`         | Parses LLM response → `Assessment` — pure function, no I/O           |
| `assessment_runner.py`         | `AssessmentRunner`; per-task grader orchestrator                     |
| `assessment_summary_writer.py` | Computes stats; writes `assessment_summary.json`                     |
| `evaluation_models.py`         | Data models: `Evaluation`, `Run`, `Assessment`, `CriterionResult`, … |
