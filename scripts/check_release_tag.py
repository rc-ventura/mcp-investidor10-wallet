#!/usr/bin/env python3
import argparse
import re
import sys
from pathlib import Path

TAG_PATTERN = re.compile(r"v(\d+\.\d+\.\d+)(rc\d+)?")
VERSION_PATTERN = re.compile(r"^__version__\s*=\s*[\"']([^\"']+)[\"']", re.MULTILINE)


def _fail(message: str) -> int:
    print(f"check_release_tag: {message}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Confere a tag de release contra __version__ e o CHANGELOG."
    )
    parser.add_argument("--tag", required=True)
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args(argv)
    root = Path(args.repo_root)

    match = TAG_PATTERN.fullmatch(args.tag)
    if match is None:
        return _fail(
            f"a tag {args.tag!r} não tem a forma vX.Y.Z ou vX.Y.ZrcN de uma release."
        )
    version = args.tag[1:]
    base = match.group(1)

    init = root / "src" / "investidor10_wallet" / "__init__.py"
    found = VERSION_PATTERN.search(init.read_text(encoding="utf-8"))
    if found is None or found.group(1) != version:
        current = found.group(1) if found else "ausente"
        return _fail(
            f"a tag pede a versão {version}, mas __version__ é {current}. "
            "Ajuste src/investidor10_wallet/__init__.py antes de criar a tag."
        )

    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    if not re.search(rf"^## \[{re.escape(base)}\]", changelog, re.MULTILINE):
        return _fail(
            f"CHANGELOG.md não tem a seção [{base}]; uma pré-versão usa a seção da "
            "versão base."
        )
    print(f"check_release_tag: tag {args.tag} confere com a versão e o CHANGELOG.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
