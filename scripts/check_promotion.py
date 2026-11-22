#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

PACKAGE = "mcp-investidor10-wallet"
REF_PATTERN = re.compile(r"promote/v(\d+\.\d+\.\d+)")
MANIFESTS = (
    "plugin/.claude-plugin/plugin.json",
    "plugin/.codex-plugin/plugin.json",
    "plugin/.devin-plugin/plugin.json",
    "plugin/gemini-extension.json",
)
BUNDLE = "plugin/servers/carteira.mcpb"
INDEX_TIMEOUT_SECONDS = 15


def tag_commit(root: Path, tag: str) -> str | None:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "rev-parse",
            "--verify",
            "--quiet",
            f"{tag}^{{commit}}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def manifest_version(root: Path, relative: str) -> str | None:
    path = root / relative
    try:
        if relative == BUNDLE:
            with zipfile.ZipFile(path) as archive:
                return json.loads(archive.read("manifest.json"))["version"]
        return json.loads(path.read_text(encoding="utf-8"))["version"]
    except (OSError, ValueError, KeyError, zipfile.BadZipFile):
        return None


def published_in_index(index_url: str, version: str) -> bool | None:
    if not index_url.startswith(("http://", "https://")):
        return None
    url = f"{index_url.rstrip('/')}/pypi/{PACKAGE}/{version}/json"
    try:
        with urllib.request.urlopen(url, timeout=INDEX_TIMEOUT_SECONDS) as response:
            return response.status == 200
    except urllib.error.HTTPError as error:
        return False if error.code == 404 else None
    except (urllib.error.URLError, OSError):
        return None


def check(head_ref: str, head_sha: str, root: Path, index_url: str) -> list[str]:
    match = REF_PATTERN.fullmatch(head_ref)
    if not match:
        message = (
            f"A origem do pedido é '{head_ref}'. Só a branch promote/vX.Y.Z, "
            "de uma versão final, pode chegar à main."
        )
        return [message]
    version = match.group(1)
    errors = []

    commit = tag_commit(root, f"v{version}")
    if commit is None:
        errors.append(f"A tag v{version} não existe neste repositório.")
    elif commit != head_sha:
        errors.append(
            f"O commit da origem ({head_sha}) não é o commit da tag v{version} ({commit})."
        )

    manifests = list(MANIFESTS)
    if (root / BUNDLE).exists():
        manifests.append(BUNDLE)
    for relative in manifests:
        found = manifest_version(root, relative)
        if found != version:
            errors.append(
                f"{relative} declara a versão {found or 'ilegível'}, "
                f"mas a promoção é da {version}."
            )

    published = published_in_index(index_url, version)
    if published is None:
        errors.append(
            "Não foi possível consultar o índice de pacotes: a promoção falha por segurança."
        )
    elif not published:
        errors.append(f"A versão {version} não está publicada no índice de pacotes.")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gate for promoting a published version to main."
    )
    parser.add_argument("--head-ref", required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--index-url", default="https://pypi.org")
    args = parser.parse_args()
    errors = check(args.head_ref, args.head_sha, args.repo_root, args.index_url)
    for error in errors:
        print(f"main-gate: {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
