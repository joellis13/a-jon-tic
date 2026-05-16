# skillevator

Runs a skill's evaluations against the Copilot CLI and records the results.

## Usage

```bash
cd .github/skills/skillevator/scripts
python take_evaluation.py --skill-name hello-user --model gpt-4.1 --times 3
```

| Flag           | Default      | Description                                  |
| -------------- | ------------ | -------------------------------------------- |
| `--skill-name` | `hello-user` | Skill directory name under `.github/skills/` |
| `--model`      | `gpt-4.1`    | Copilot model passed to `--model`            |
| `--times`      | `3`          | Number of runs per evaluation prompt         |

## Execution Order

```
take_evaluation.py          ← CLI entry point
│
├── parse_args()            ← resolve --skill-name / --model / --times
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
        ├── get_split_evaluations()     ← duplicate each eval: with_skill + without_skill
        │
        └── EvaluationRunner.run_task() ← per task (runs concurrently)
            ├── copy .github/ into a temp dir
            ├── optionally remove the skill folder (without_skill variant)
            ├── CopilotCommandRunner.run()      → CopilotResponse
            ├── CopilotResponse.format_summary()  → print progress
            ├── RunFactory.create()             → Run
            ├── RunDirectoryWriter.write()      → files on disk
            └── collect new files → Run.files
```

After all tasks complete, results are aggregated back into the `SkillEvaluation`
and written to `evaluations/<skill>/evals.json`.

## Module Map

| File                      | Responsibility                                                        |
| ------------------------- | --------------------------------------------------------------------- |
| `take_evaluation.py`      | CLI entrypoint; wires dependencies; orchestrates the run              |
| `evaluation_config.py`    | `EvaluationConfig` dataclass; all path resolution                     |
| `command_runner.py`       | `CopilotCommandRunner`; owns `subprocess`                             |
| `copilot_models.py`       | `CopilotResponse`; parses CLI stdout/stderr                           |
| `run_factory.py`          | `RunFactory`; builds `Run` from response — no I/O                     |
| `run_directory_writer.py` | `RunDirectoryWriter`; writes output files — no logic                  |
| `evaluation_runner.py`    | `EvaluationRunner`; per-task orchestrator; all collaborators injected |
| `evaluation_models.py`    | Data models: `Evaluation`, `Run`, `RunTask`, `SkillEvaluation`, …     |
