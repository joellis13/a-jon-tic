import json, os, re, sys

workspace = r"C:\Users\joell\repos\a-jon-tic\.github\skills\hello-user-workspace\iteration-1"

def is_ascii_art(text):
    lines = [l for l in text.splitlines() if re.search(r'[|_/\\]', l)]
    return len(lines) >= 4

def has_figlet_style(text):
    return bool(re.search(r'\|.+\|', text, re.MULTILINE)) and is_ascii_art(text)

def has_code_block(text):
    return '```' in text

cases = [
    ("eval-1-hello",        "with_skill",    4),
    ("eval-1-hello",        "without_skill", 4),
    ("eval-2-hey-copilot",  "with_skill",    4),
    ("eval-2-hey-copilot",  "without_skill", 4),
    ("eval-3-hello-copilot","with_skill",    5),
    ("eval-3-hello-copilot","without_skill", 5),
]

username = "joell"

results = {}
for (eval_name, config, _) in cases:
    path = os.path.join(workspace, eval_name, config, "outputs", "output.txt")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    results[(eval_name, config)] = {
        "ascii_art":     is_ascii_art(text),
        "hello_literal": "hello" in text.lower(),
        "username":      username in text.lower(),
        "code_block":    has_code_block(text),
        "figlet_style":  has_figlet_style(text),
    }
    print(f"--- {eval_name} / {config} ---")
    for k, v in results[(eval_name, config)].items():
        print(f"  {k}: {v}")
    print()
