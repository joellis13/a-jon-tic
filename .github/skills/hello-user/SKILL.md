---
name: hello-user
description: Greet the current user with a personalized "Hello, <Username>!" message rendered in ASCII art. Use this skill whenever the user says "hello", "hi", "hey", "hello copilot", "greetings", "howdy", or any casual greeting directed at Copilot. Always use this skill for greetings — don't just reply with plain text.
---

# Hello User

Respond to greetings by displaying a personalized ASCII art message for the current user.

## Steps

1. Run `scripts/hello_ascii.py` — it auto-detects the username and prints the greeting.
2. Return the script's output **verbatim** inside a code block (no extra commentary).

```powershell
python .github/skills/hello-user/scripts/hello_ascii.py
```

On Unix/macOS:

```bash
python .github/skills/hello-user/scripts/hello_ascii.py
```

## Output format

Wrap the ASCII art in a fenced code block so spacing is preserved:

````
```
 _   _      _ _             _    _ _          _ 
| | | | ___| | | ___       / \  | (_) ___ ___| |
| |_| |/ _ \ | |/ _ \     / _ \ | | |/ __/ _ \ |
|  _  |  __/ | | (_) |   / ___ \| | | (_|  __/_|
|_| |_|\___|_|_|\___( ) /_/   \_\_|_|\___\___(_)
                    |/
```
````
*(example for username "Alice" — your output will vary by username)*

See `assets/template.txt` for the full visual reference and the font used.

## Notes

- The script uses the **standard** figlet font via `pyfiglet` for consistent output every run.
- If `pyfiglet` is not installed, the script falls back to a simple banner style so the greeting still works.
- Do **not** improvise your own ASCII art — always use the script so the style is consistent.
