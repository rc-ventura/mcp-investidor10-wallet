import argparse
import asyncio
import datetime
import shutil
import sys
from pathlib import Path

from .. import wallet_client, wallet_config
from . import ClientRegistration, InstallerSession, RegisterOutcome
from .clients import ADAPTERS, RUNNER_ARGS, RUNNER_COMMAND, _run

VALID_CLIENTS = {"claude", "devin", "codex", "gemini"}

EXIT_INVALID_INPUT = 2
EXIT_REFUSED = 3
EXIT_UNAVAILABLE = 4

PRIVACY_NOTICE = (
    "Privacidade: veja https://github.com/rc-ventura/mcp-investidor10-wallet"
    "/blob/main/docs/PRIVACY.md"
)

YES_ANSWERS = ("s", "sim", "y", "yes")

LINK_PROMPT = "Cole o link da sua carteira do Investidor10 (ou só o número dela): "
NO_TERMINAL_MESSAGE = (
    "Não foi possível ler o link da carteira (entrada não-interativa). Use --link LINK."
)
ACCESS_DENIED_RESTRICTED = (
    "O Investidor10 recusou o acesso à carteira. O link restrito pode ter sido "
    "renovado ou a carteira pode ter virado privada. Gere o link de "
    "compartilhamento atual no site e tente de novo, ou deixe a carteira pública."
)
ACCESS_DENIED_PUBLIC = (
    "O Investidor10 recusou o acesso à carteira. Se ela for restrita, cole o link "
    "completo, com o trecho ?h=...; se for privada, torne-a pública ou restrita "
    "nas configurações do site."
)
NOT_FOUND_MESSAGE = (
    "Carteira não encontrada. Confira o link ou o número da carteira e tente de novo."
)
UNAVAILABLE_PROMPT = (
    "O Investidor10 não respondeu agora, então não foi possível validar a carteira. "
    "Salvar a configuração mesmo assim [s/N]? "
)
UNAVAILABLE_DECLINED_MESSAGE = (
    "Configuração não salva: a carteira não pôde ser validada. Tente de novo "
    "quando o Investidor10 voltar a responder."
)
SWITCH_PROMPT = (
    "A carteira informada é diferente da que está configurada. A memória (teses, "
    "regras, decisões e alertas) é única por usuário e continuará valendo para a "
    "nova carteira. Trocar de carteira [s/N]? "
)
SWITCH_DECLINED_MESSAGE = "Configuração mantida: a carteira não foi trocada."
SWITCH_NO_TERMINAL_MESSAGE = (
    "Trocar de carteira exige confirmação e não há terminal para perguntar. "
    "Rode 'mcp-investidor10-wallet configure' num terminal."
)
FUTURE_VERSION_MESSAGE = (
    "A configuração local foi criada por uma versão mais nova do produto e não "
    "será alterada. Atualize o mcp-investidor10-wallet e tente de novo."
)
PUBLIC_WARNING = (
    "Atenção: a carteira pública pode ser indexada por buscadores. Recomendação: "
    "use o link de carteira restrita (compartilhar com link, no site do "
    "Investidor10)."
)
MASK_PROMPT = (
    "Ativar o modo privacidade? Ele impede que valores em reais e quantidades "
    "cheguem ao modelo; percentuais e cotações continuam, mas patrimônio, lucro, "
    "histórico e proventos em reais deixam de existir (detalhes em docs/PRIVACY.md) "
    "{choices}? "
)
SAVE_FAILED_MESSAGE = "Não foi possível gravar a configuração local ({cause})."
UNCHANGED_MESSAGE = "Configuração local inalterada: as respostas são as mesmas."
CONFIG_LOCATION = "~/.investidor10/config.json"


def _add_wallet_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--link",
        help="link da carteira, pública ou restrita (sem esta flag, o assistente pergunta)",
    )
    parser.add_argument(
        "--mask",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="liga (--mask) ou desliga (--no-mask) o modo privacidade sem perguntar",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="pula confirmações de rotina (não responde as perguntas de colisão de alias, fonte indisponível e troca de carteira)",
    )


def _parse(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mcp-investidor10-wallet install",
        description="Instala o produto da carteira nos CLIs de agente da máquina: grava a configuração local, registra o servidor MCP e instala o plugin de comportamento.",
    )
    parser.add_argument(
        "--clients",
        help="clientes alvo separados por vírgula (claude,devin,codex,gemini); padrão: todos os detectados",
    )
    _add_wallet_arguments(parser)
    parser.add_argument(
        "--wallet-id",
        help="ID da carteira pública (forma antiga de --link)",
    )
    parser.add_argument(
        "--mcp-only",
        action="store_true",
        help="registra apenas o servidor MCP, sem instalar o plugin de comportamento",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="simula a detecção e o relatório sem registrar nada",
    )
    return parser.parse_args(argv)


def _parse_configure(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mcp-investidor10-wallet configure",
        description="Refaz a configuração local da carteira (link e modo privacidade) sem registrar nem instalar nada.",
    )
    _add_wallet_arguments(parser)
    args = parser.parse_args(argv)
    args.wallet_id = None
    return args


def _ask(prompt: str) -> str | None:
    try:
        return input(prompt).strip().lower()
    except (EOFError, OSError):
        return None


def _confirm(prompt: str) -> bool | None:
    answer = _ask(prompt)
    if answer is None:
        return None
    return answer in YES_ANSWERS


def _link_text(args: argparse.Namespace) -> str | None:
    if args.link:
        return args.link
    if args.wallet_id:
        return args.wallet_id
    try:
        return input(LINK_PROMPT)
    except (EOFError, OSError):
        print(NO_TERMINAL_MESSAGE, file=sys.stderr)
        return None


def _choose_mask(args: argparse.Namespace, current_mask: bool) -> bool:
    if args.mask is not None:
        return args.mask
    choices = "[S/n]" if current_mask else "[s/N]"
    answer = _ask(MASK_PROMPT.format(choices=choices))
    if not answer:
        return current_mask
    return answer in YES_ANSWERS


def _summary(config: wallet_config.LocalConfig) -> None:
    kind = (
        "restrita (acesso pelo link de compartilhamento)"
        if config.mode == "restricted"
        else "pública"
    )
    mask = "ligado" if config.mask_values else "desligado"
    print(f"Configuração salva em {CONFIG_LOCATION}.")
    print(f"- Carteira: {kind}")
    print(f"- Modo privacidade: {mask}")


def _configure_wallet(args: argparse.Namespace, source: str, dry_run: bool) -> int:
    text = _link_text(args)
    if text is None:
        return EXIT_INVALID_INPUT
    try:
        link = wallet_config.parse_link(text)
    except wallet_config.LinkError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_INVALID_INPUT
    path = wallet_config.config_path(Path.home())
    current = None
    try:
        current = wallet_config.read_config(path)
    except wallet_config.ConfigProblem as problem:
        if problem.reason == "future_version":
            print(FUTURE_VERSION_MESSAGE, file=sys.stderr)
            return EXIT_INVALID_INPUT
    result = asyncio.run(wallet_client.check_wallet(link.wallet_id, link.share_hash))
    if result == "access_denied":
        message = (
            ACCESS_DENIED_RESTRICTED
            if link.mode == "restricted"
            else ACCESS_DENIED_PUBLIC
        )
        print(message, file=sys.stderr)
        return EXIT_REFUSED
    if result == "not_found":
        print(NOT_FOUND_MESSAGE, file=sys.stderr)
        return EXIT_REFUSED
    if result == "unavailable" and _confirm(UNAVAILABLE_PROMPT) is not True:
        print(UNAVAILABLE_DECLINED_MESSAGE, file=sys.stderr)
        return EXIT_UNAVAILABLE
    if current is not None and current.wallet_id != link.wallet_id:
        switch = _confirm(SWITCH_PROMPT)
        if switch is None:
            print(SWITCH_NO_TERMINAL_MESSAGE, file=sys.stderr)
            return EXIT_INVALID_INPUT
        if not switch:
            print(SWITCH_DECLINED_MESSAGE)
            return 0
    if link.mode == "public":
        print(PUBLIC_WARNING)
    mask = _choose_mask(args, current.mask_values if current else False)
    unchanged = current is not None and (
        current.wallet_id,
        current.share_hash,
        current.mode,
        current.mask_values,
    ) == (link.wallet_id, link.share_hash, link.mode, mask)
    if unchanged:
        print(UNCHANGED_MESSAGE)
        return 0
    config = wallet_config.LocalConfig(
        wallet_id=link.wallet_id,
        share_hash=link.share_hash,
        mode=link.mode,
        mask_values=mask,
        validated_at=datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        source=source,
    )
    if dry_run:
        print("- configuração local: seria gravada")
        return 0
    try:
        wallet_config.write_config(Path.home(), config)
    except OSError as exc:
        print(SAVE_FAILED_MESSAGE.format(cause=exc.strerror or "erro"), file=sys.stderr)
        return EXIT_INVALID_INPUT
    _summary(config)
    return 0


def run_configure(argv: list[str]) -> int:
    """Entry point of the configure subcommand."""
    args = _parse_configure(argv)
    return _configure_wallet(args, "configure", dry_run=False)


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
    requested = (
        {item.strip() for item in args.clients.split(",")} if args.clients else None
    )
    if requested is not None:
        invalid = requested - VALID_CLIENTS
        if invalid:
            print(
                f"Clientes inválidos em --clients: {', '.join(sorted(invalid))}. "
                f"Válidos: {', '.join(sorted(VALID_CLIENTS))}.",
                file=sys.stderr,
            )
            return 2
    if args.dry_run:
        print("SIMULAÇÃO (nenhuma configuração foi alterada)")
    code = _configure_wallet(args, "installer", dry_run=args.dry_run)
    if code != 0:
        return code
    adapters = [a for a in ADAPTERS if requested is None or a.client_id in requested]
    detected = [a for a in adapters if a.detect()]
    absent = [a for a in adapters if not a.detect()] if requested is not None else []
    if not detected:
        for adapter in absent:
            print(f"- {adapter.label}: não encontrado na máquina", file=sys.stderr)
        print(
            "Nenhum cliente de agente detectado. Instale Claude Code, Devin CLI, "
            "Codex ou Gemini CLI e rode o assistente novamente.",
            file=sys.stderr,
        )
        return 1
    reg = ClientRegistration(command=RUNNER_COMMAND, args=list(RUNNER_ARGS))
    if args.dry_run:
        for adapter in detected:
            if adapter.client_id == "claude" and not args.mcp_only:
                print(
                    f"- {adapter.label}: instalaria o plugin, que já traz o "
                    "servidor 'carteira'"
                )
                continue
            print(f"- {adapter.label}: registraria o servidor 'carteira'")
            if not args.mcp_only:
                print(f"- {adapter.label}: instalaria o plugin")
        for adapter in absent:
            print(f"- {adapter.label}: não encontrado na máquina")
        return 0
    session = InstallerSession(requested={a.client_id for a in detected})
    for adapter in absent:
        session.outcomes.append(
            RegisterOutcome(
                adapter.client_id,
                "skipped_absent",
                f"{adapter.label}: não encontrado na máquina — pulado.",
            )
        )
    for adapter in detected:
        if adapter.client_id == "claude" and not args.mcp_only:
            outcome, steps = adapter.install_plugin()
            session.outcomes.append(outcome)
            session.plugin_outcomes.extend(steps)
            continue
        outcome = adapter.register(reg)
        session.outcomes.append(outcome)
        if args.mcp_only or outcome.status == "failed":
            continue
        commands = adapter.plugin_install_commands()
        if not commands:
            session.plugin_outcomes.append(
                RegisterOutcome(
                    adapter.client_id,
                    "failed",
                    f"{adapter.label}: plugin não suportado nesta versão do CLI "
                    "(Codex requer v0.122+); atualize e rode o assistente novamente.",
                )
            )
            continue
        for command in commands:
            proc = _run(command)
            if proc.returncode == 0:
                session.plugin_outcomes.append(
                    RegisterOutcome(
                        adapter.client_id,
                        "registered",
                        f"{adapter.label}: plugin instalado (reinicie a sessão do cliente).",
                    )
                )
            else:
                detail = proc.stderr.strip() or f"código {proc.returncode}"
                session.plugin_outcomes.append(
                    RegisterOutcome(
                        adapter.client_id,
                        "failed",
                        f"{adapter.label}: falha ao instalar o plugin — {detail}",
                    )
                )
    for outcome in session.outcomes:
        print(f"- {outcome.message}")
    for outcome in session.plugin_outcomes:
        print(f"- {outcome.message}")
    print(PRIVACY_NOTICE)
    if session.outcomes and all(
        o.status in ("failed", "skipped_absent") for o in session.outcomes
    ):
        return 4
    return 0
