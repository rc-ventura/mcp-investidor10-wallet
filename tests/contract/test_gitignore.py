from pathlib import Path

GITIGNORE = Path(__file__).resolve().parents[2] / ".gitignore"

PATTERNS = (
    "memory.json",
    "memory.json.log",
    "memory.json.lock",
    "*.broken-*",
    ".memory-*",
)


def test_memory_sidecar_files_are_ignored_by_git():
    lines = {line.strip() for line in GITIGNORE.read_text().splitlines()}
    for pattern in PATTERNS:
        assert pattern in lines, pattern
