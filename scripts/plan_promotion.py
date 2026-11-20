#!/usr/bin/env python3
import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

FINAL_TAG = re.compile(r"v\d+\.\d+\.\d+")
CANDIDATE_TAG = re.compile(r"v\d+\.\d+\.\d+rc\d+")


class PromotionRefused(Exception):
    pass


@dataclass(frozen=True)
class Action:
    kind: str
    branch: str = ""
    sha: str = ""
    head: str = ""
    base: str = ""
    tag: str = ""

    def describe(self) -> str:
        if self.kind == "create_branch":
            return (
                f"criar a branch {self.branch} no commit {self.sha} da tag {self.tag}"
            )
        return f"abrir o pedido de {self.head} para {self.base}"

    def commands(self) -> list[list[str]]:
        if self.kind == "create_branch":
            return [["git", "push", "origin", f"{self.sha}:refs/heads/{self.branch}"]]
        title = f"Promover {self.tag} para {self.base}"
        body = (
            f"Promoção automática da versão {self.tag}, já publicada no índice. "
            "O main-gate confere a tag, os manifestos e o índice."
        )
        return [
            [
                "gh", "pr", "create",
                "--base", self.base,
                "--head", self.head,
                "--title", title,
                "--body", body,
            ]
        ]  # fmt: skip


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=False
    )


def _commit_of(root: Path, ref: str) -> str | None:
    result = _git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    return result.stdout.strip() if result.returncode == 0 else None


def final_tag_at(root: Path, sha: str) -> str | None:
    result = _git(root, "tag", "--points-at", sha)
    tags = sorted(t for t in result.stdout.split() if FINAL_TAG.fullmatch(t))
    return tags[-1] if tags else None


def plan(tag: str, root: Path, develop_ref: str = "origin/develop") -> list[Action]:
    if CANDIDATE_TAG.fullmatch(tag):
        raise PromotionRefused(
            f"A tag {tag} é de pré-lançamento: pré-lançamentos nunca chegam à main."
        )
    if not FINAL_TAG.fullmatch(tag):
        raise PromotionRefused(
            f"A tag {tag!r} não tem a forma vX.Y.Z de uma versão final."
        )
    sha = _commit_of(root, f"refs/tags/{tag}")
    if sha is None:
        raise PromotionRefused(f"A tag {tag} não existe neste repositório.")
    if _commit_of(root, develop_ref) is None:
        raise PromotionRefused(
            f"A referência {develop_ref} não existe: busque a develop antes de planejar."
        )
    branch = f"promote/{tag}"
    actions = [
        Action("create_branch", branch=branch, sha=sha, tag=tag),
        Action("open_pull_request", head=branch, base="main", tag=tag),
    ]
    in_develop = _git(root, "merge-base", "--is-ancestor", sha, develop_ref)
    if in_develop.returncode == 1:
        actions.append(
            Action("open_pull_request", head=branch, base="develop", tag=tag)
        )
    elif in_develop.returncode != 0:
        raise PromotionRefused(
            f"Não foi possível comparar a tag {tag} com {develop_ref}."
        )
    return actions


def apply(actions: list[Action], root: Path) -> None:
    for action in actions:
        for command in action.commands():
            subprocess.run(command, cwd=root, check=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Planeja (e, com --apply, executa) a promoção de uma versão final para a main."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--tag", help="tag final já publicada (vX.Y.Z)")
    source.add_argument("--sha", help="commit do release; a tag final é procurada nele")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--develop-ref", default="origin/develop")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="executa as ações; sem esta flag, só imprime (simulação)",
    )
    args = parser.parse_args(argv)
    tag = args.tag
    if tag is None:
        if _commit_of(args.repo_root, args.sha) is None:
            print(
                f"plan_promotion: o commit {args.sha} não existe neste repositório.",
                file=sys.stderr,
            )
            return 1
        tag = final_tag_at(args.repo_root, args.sha)
        if tag is None:
            print(
                f"Nada a promover: o commit {args.sha} não tem tag de versão final "
                "(pré-lançamentos não são promovidos)."
            )
            return 0
    try:
        actions = plan(tag, args.repo_root, args.develop_ref)
    except PromotionRefused as refused:
        print(f"plan_promotion: {refused}", file=sys.stderr)
        return 1
    header = "Ações" if args.apply else "Simulação (nada foi alterado). Ações"
    print(f"{header} para {tag}:")
    for action in actions:
        print(f"- {action.describe()}")
    if args.apply:
        apply(actions, args.repo_root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
