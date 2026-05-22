import difflib
import hashlib
from pathlib import Path


def snapshot(root: Path) -> dict[str, str]:
    """Return {relative_path_str: sha256_hex} for every file under root."""
    return {
        str(f.relative_to(root)): hashlib.sha256(f.read_bytes()).hexdigest()
        for f in root.rglob("*") if f.is_file()
    }


def compute_changes(before: dict[str, str], after: dict[str, str]) -> dict:
    """Diff two snapshots. Returns lists of relative path strings for each change type."""
    return {
        "created":  [p for p in after if p not in before],
        "modified": [p for p in after if p in before and after[p] != before[p]],
        "deleted":  [p for p in before if p not in after],
        "diffs":    {},
    }


def generate_diff(original: Path, modified: Path) -> str | None:
    """Return a unified diff string between two files.

    Returns an empty string if the files are identical, None if either
    file cannot be read as text (binary or missing).
    """
    try:
        before_lines = original.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        after_lines  = modified.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    except OSError:
        return None
    diff = list(difflib.unified_diff(
        before_lines,
        after_lines,
        fromfile=f"a/{original.name}",
        tofile=f"b/{original.name}",
    ))
    return "".join(diff)


def generate_creation_diff(created: Path) -> str | None:
    """Return a unified diff for a newly created file (empty → new content).

    Returns None if the file cannot be read as text (binary or missing).
    """
    try:
        after_lines = created.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    except OSError:
        return None
    diff = list(difflib.unified_diff(
        [],
        after_lines,
        fromfile="/dev/null",
        tofile=f"b/{created.name}",
    ))
    return "".join(diff)
