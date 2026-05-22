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
    }
