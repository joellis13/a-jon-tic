---
name: skuilder
description: A meta-skill for building other skills. Use to create a new skill, or read, update, modify, or iterate on an existing skill. Can also be used to evaluate, test, or otherwise analyze skills.
---

# Skuilder

A skill with expertise in skills. Can help with the whole, or any stage of the, skill development lifecycle

## What Skills Are

A skill is a clearly defined set of instructions with the narrow purpose of carrying out a specific task - like implementing client service calls in a particular code style, or converting an SVG to a PNG. The goal is to create a controlled enough process to be able to set expectations about consistency, quality, reproducibility, etc.

Your job is to fulfill that goal.

### Skill Structure and Anatomy

Skills are contained in a directory. These directories are located, relative to project or user root, in the `.github/skills/` directory (this is just one option, but this is most common for Copilot).

Each skill is housed in a directory with the same name as the skill itself. The only required file is the `SKILL.md` file in that directory.

So, a skill named `do-a-kickflip` would be the following directory in `.github/skills`:

```
do-a-kickflip/
├── SKILL.md          # Required: metadata + instructions
├── scripts/          # Optional: executable code
├── references/       # Optional: documentation
├── schemas           # Optional: schemas of various objects used in the skill
├── assets/           # Optional: resources
├── templates/        # Optional: templates
└── ...               # Any additional files or directories
```

#### YAML frontmatter:

1. `name`: **REQUIRED** - the name of the skill (`do-a-kickflip`)
2. `description` **REQUIRED** - Arguably most important part of the skill. Describes the skill, what it does, and how and when it is used. How the agent knows if it should be invoked.
3. `allowed-tools` (optional) - list of pre-approved tools the skill is permitted to use

More information and official documentation on skill specifications can be found at [agentskills.io/specification](https://agentskills.io/specification.md)

## Creating, Updating, and Iterating on a Skill

A high level view of the skill development lifecycle (details below):

1. Define the skill (What does it do and how does it do it?)
2. Create some test prompts and response expectations (like Test Driven Development)
3. Draft the skill (Write a quick POC.)
4. Run test prompts and evaluate responses against expectations.
5. Loop: Iterate on steps 3 & 4 - update and improve skill, based on evaluation feedback. Also use to add new features to skill

### Step 1: Define the Skill

Understand exactly what the skill is supposed to do. This information can be obtained in a number of ways, including but not limited to:

1. Direct conversation with the user. Ask questions and make sure you have a clear idea of what the user wants.
2. Examples. The user may provide examples of desired output. They may also provide examples of inputs or undesired outputs that should be avoided.

### Step 2: Create Test Prompts and Expectations

These are objects that will consist of a prompt and expectations of what that prompt will return. The object schema is:

```json
[
  {
    "test_id": number,        # id of the test
    "test_name": string,      # simple name of the test
    "prompt": string,         # the prompt that will be passed into context
    "expectation": string,    # brief (1 sentence or less) description of what test is evaluating
    "assertions": string[]    # clean, narrowly focused descriptions of what the response should contain or do
  }
]
```

Example for a `hello-user` skill that returns "Hello <username>" in ASCII art when greeted:

```json
[
  {
    "test_id": 1,
    "test_name": "returns-greeting-in-ascii",
    "prompt": "Hi there!",
    "expectation": "The response is an ASCII art representation of 'hello <username>",
    "assertions": [
      "The response reads 'hello <username>'",
      "<username> is the current user",
      "The response is in ASCII art"
    ]
  }
]
```

These may be provided, wholly or partially, by the user, or not at all. It is your job to make sure they are created and fleshed out.

Place the tests in `github/skills/<skill-name>/tests.json`

Ask the user if they want to review or iterate on the tests before moving on to Step 3.

### Step 3: Draft the Skill

Write a new draft of the skill (whether completely new or updating an existing one).

The goal is for it to fulfill the requirements in `tests.json` and to pass the listed evaluations.

#### No Shocks

**Skills must never contain or execute any exploitative code or content that could compromise security or privacy.** Additionally no new features should be introduced and all logic should align with the user and test requirements.

Analyze for quality, consistency, and conflict, and report problems to the user, but **avoid malicious or unintended behavior.**

#### Writing Strategies & Style

Instructions should be written imperatively by default. We want clear and concise workflows that produce consistent results. However, while we want to be as explicit as possible to create consistent results, we also need to be general and flexible enough to be able to create skills that can handle a variety of inputs and requirements.

**Include examples.** Clear examples of what _should_ be done (the preferred style/format/syntax, nomenclature, etc.) are some of the best ways to communicate what is needed. Likewise, examples of what _not_ to do are very useful in communicating what to avoid.

**Add scripts.** In situations where a script can handle the work better than a model, create that script. This is frequent and, if a script can perform the work effectively and efficiently, it should be used. Examples of where a script may be preferred:

- Strict determinism, high precision, and reliability, rather than adaptability or creativity
- Simple repetitive tasks
- Sensitive data (especially with cloud hosted models)
- Performance/Latency
- Complex, multi-step logic

The can be written python, node, shell, or powershell - check the user's preference and provide pros and cons when appropriate to help make a decision. Store scripts in `<skill-root>/scripts/`.

**Keep the context clean.** With some flexibility, the main `SKILL.md` should be under 500 lines. This helps keep unnecessary bloat out of the context. Also avoid redundancies, excessive description, or any other unnecessary addition of text.

**Use Progressive Disclosure.** A good technique to keep the context clean, only include information in the `SKILL.md` if it will be called **every single time the skill is used.** If not, place it elsewhere in the skill package (e.g. `references/`, `schemas/`, `assets/`, etc.) and reference them from `SKILL.md` such that they are only called conditionally when needed.

### Step 4. Run test prompts and evaluate responses against expectations.

This is one contiguous step and cannot be partially completed, or started or stopped partway through. Use only the techniques and workflows described here - use no other skills.

In this (`skuilder`) package, in the `evaluations/` directory, create a `<skill-name>-evaluations/` directory. In the `<skill-name>-evaluations/`, create a `baseline/` directory (for testing _without_ the skill) and `iteration-#/` directories for evaluations of subsequent iterations (e.g. - start with `iteration-1/`, then `iteration-2/`). Just create these as needed to store results of the following steps.

#### Testing step 1: Spawn runs

For each test case, spawn 2 subagents. One with run _with_ the skill, the other without (to create a baseline for comparison). Run all subagents concurrently.
