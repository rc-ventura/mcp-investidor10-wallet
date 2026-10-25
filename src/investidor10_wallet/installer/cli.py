import argparse
import asyncio
import shutil
import sys

from .. import wallet_client
from . import ClientRegistration, InstallerSession
from .clients import ADAPTERS

PLUGIN_INSTRUCTIONS = (
    "Para instalar o plugin de comportamento:\n"
    "  Claude Code: claude plugin marketplace add rc-ventura/mcp-investidor10-wallet\n"
    "               depois rode: /plugin install investidor10-carteira\n"
    "  Devin CLI: instale o plugin do mesmo repositório com `devin plugins install`\n"
)


def _parse(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mcp-investidor10-wallet install",
        description="Registra o servidor da carteira nos CLIs de agente da máquina.",
    )
    parser.add_argument(
        "--clients",
        help="clientes alvo separados por vírgula (claude,devin,codex,gemini); padrão: todos os detectados",
    )
    parser.add_argument(
        "--wallet-id",
        help="ID público da carteira (sem esta flag, o assistente pergunta)",
    )
    parser.add_argument(
        "--plugin",
        action="store_true",
        help="ao final, imprime as instruções de instalação do plugin de comportamento",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="simula a detecção e o relatório sem registrar nada",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="pula confirmações de rotina (não afeta a pergunta de colisão de alias)",
    )
    return parser.parse_args(argv)


def _wallet_id(args: argparse.Namespace) -> str:
    if args.wallet_id:
        return args.wallet_id
    return input(
        "Informe o ID da carteira (o número na URL investidor10.com.br/carteira/SEU_ID): "
    ).strip()


def _validate_wallet(wallet_id: str) -> bool:
    try:
        asyncio.run(wallet_client.validate_wallet(wallet_id))
    except SystemExit as exc:
        print(
            f"{exc}\nCorrija o ID ou torne a carteira pública e tente novamente.",
            file=sys.stderr,
        )
        return False
    return True


def _maybe_print_plugin(args: argparse.Namespace) -> None:
    if args.plugin:
        print(PLUGIN_INSTRUCTIONS)


def run(argv: list[str]) -> int:
    """Entry point of the install assistant."""
    args = _parse(argv)
    if shutil.which("uv") is None:
        print(
            "O runner 'uv' não foi encontrado. Instale com: "
            "curl -LsSf https://astral.sh/uv/install.sh | sh",
            file=sys.stderr,
        )
        return 2
    wallet_id = _wallet_id(args)
    if not _validate_wallet(wallet_id):
        return 3
    requested = (
        {item.strip() for item in args.clients.split(",")} if args.clients else None
    )
    adapters = [a for a in ADAPTERS if requested is None or a.client_id in requested]
    detected = [a for a in adapters if a.detect()]
    if not detected:
        print(
            "Nenhum cliente de agente detectado. Instale Claude Code, Devin CLI, "
            "Codex ou Gemini CLI e rode o assistente novamente.",
            file=sys.stderr,
        )
        return 1
    reg = ClientRegistration(
        command="uvx",
        args=["mcp-investidor10-wallet"],
        env={"WALLET_ID": wallet_id},
    )
    if args.dry_run:
        print("SIMULAÇÃO (nenhuma configuração foi alterada)")
        for adapter in detected:
            print(f"- {adapter.label}: registraria o servidor 'carteira'")
        _maybe_print_plugin(args)
        return 0
    session = InstallerSession(
        wallet_id=wallet_id, requested={a.client_id for a in detected}
    )
    for adapter in detected:
        session.outcomes.append(adapter.register(reg))
    for outcome in session.outcomes:
        print(f"- {outcome.message}")
    _maybe_print_plugin(args)
    if session.outcomes and all(o.status == "failed" for o in session.outcomes):
        return 4
    return 0
