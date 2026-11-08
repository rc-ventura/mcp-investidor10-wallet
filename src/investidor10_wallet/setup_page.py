import asyncio
import datetime
import html
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from . import wallet_client, wallet_config

HOST = "127.0.0.1"
TOKEN_TTL_SECONDS = 600
MAX_BODY_BYTES = 65536
MAX_DISCARD_BYTES = 1024 * 1024
TERMINAL_ALTERNATIVE = "mcp-investidor10-wallet configure"

clock = time.monotonic

OPENED_MESSAGE = (
    "The wallet setup page is open in the user's browser on this computer. Ask the "
    "user to paste their Investidor10 wallet link there, never in this conversation, "
    "choose the privacy mode and save, then tell you. After that, call "
    "get_session_context and check the configuration block."
)
ALREADY_OPEN_MESSAGE = (
    "The wallet setup page was already open; the browser was asked to show it again. "
    "Ask the user to paste their Investidor10 wallet link there, never in this "
    "conversation, choose the privacy mode and save, then tell you. After that, call "
    "get_session_context and check the configuration block."
)
OPEN_MANUALLY_MESSAGE = (
    "The browser could not be opened. Ask the user to open setup_url in a browser on "
    "this computer: it only accepts the setup form and expires in 10 minutes. Or ask "
    "them to run terminal_alternative in a terminal. Never ask for the wallet link in "
    "this conversation."
)

VALID_FORMS = (
    "Formas aceitas: o link da carteira restrita (o link de compartilhamento do "
    "Investidor10, que termina em ?h=...), o link da carteira pública "
    "(https://investidor10.com.br/wallet/public/ seguido do número, sem ?h=) ou "
    "só o número da carteira."
)
MASK_HELP = (
    "O modo privacidade impede que valores em reais e quantidades cheguem ao modelo. "
    "Continuam disponíveis os percentuais, a alocação, os fundamentos e as cotações; "
    "deixam de existir o patrimônio, o lucro, o histórico de patrimônio e os "
    "proventos em reais."
)
PUBLIC_WARNING = (
    "A carteira pública pode ser indexada por buscadores. A carteira restrita (link "
    "de compartilhamento) é a recomendada."
)

STYLE = (
    "body{font-family:system-ui,sans-serif;max-width:40rem;margin:2rem auto;"
    "padding:0 1rem;line-height:1.5;color:#1d1d1f;background:#fff}"
    "input[type=password],input[type=text]{width:100%;padding:.5rem;font-size:1rem;"
    "box-sizing:border-box}button{padding:.5rem 1rem;font-size:1rem;margin-top:1rem}"
    ".warn{background:#fff4e5;padding:.75rem;border-radius:.25rem}"
    ".error{background:#fdecea;padding:.75rem;border-radius:.25rem}"
    "small{color:#555}"
)
TOGGLE_SCRIPT = (
    "document.getElementById('show').addEventListener('change',function(e){"
    "document.getElementById('link').type=e.target.checked?'text':'password';});"
)


class SetupUnavailable(Exception):
    pass


def _csp(nonce: str) -> str:
    return (
        "default-src 'none'; style-src 'unsafe-inline'; "
        f"script-src 'nonce-{nonce}'; form-action 'self'; "
        "frame-ancestors 'none'; base-uri 'none'"
    )


def _layout(result: str, content: str, nonce: str, script: bool = False) -> str:
    tag = f'<script nonce="{nonce}">{TOGGLE_SCRIPT}</script>' if script else ""
    return (
        '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Configurar carteira</title>"
        f"<style>{STYLE}</style></head><body>"
        f'<main data-result="{result}"><h1>Configurar carteira do Investidor10</h1>'
        f"{content}</main>{tag}</body></html>"
    )


def _mode_label(mode: str) -> str:
    return "restrita" if mode == "restricted" else "pública"


def _current_line(current) -> str:
    if current is None:
        return ""
    mask = "ligado" if current.mask_values else "desligado"
    return (
        f"<p>Configuração atual: carteira {_masked(current.wallet_id)} "
        f"({_mode_label(current.mode)}), modo privacidade {mask}.</p>"
    )


def _masked(wallet_id: str) -> str:
    return html.escape(wallet_config.masked_wallet(wallet_id))


def _form(session, current, nonce: str, notice: str = "") -> str:
    checked = " checked" if current is not None and current.mask_values else ""
    return (
        f"{notice}{_current_line(current)}"
        '<form method="post" action="/" autocomplete="off">'
        f'<input type="hidden" name="token" value="{html.escape(session.token)}">'
        '<input type="hidden" name="action" value="save">'
        '<p><label for="link">Link da carteira</label><br>'
        '<input type="password" id="link" name="link" required '
        'autocomplete="off" spellcheck="false"></p>'
        '<p><label><input type="checkbox" id="show"> Mostrar o link</label></p>'
        f"<p><small>{html.escape(VALID_FORMS)}</small></p>"
        f'<p><label><input type="checkbox" name="mask"{checked}> '
        "Ligar o modo privacidade</label><br>"
        f"<small>{html.escape(MASK_HELP)}</small></p>"
        '<button type="submit">Salvar</button></form>'
        "<p><small>Cole o link aqui, nunca na conversa com o assistente.</small></p>"
    )


def _notice(kind: str, text: str) -> str:
    return f'<p class="{kind}">{html.escape(text)}</p>'


class SetupSession:
    def __init__(self) -> None:
        self.token = secrets.token_urlsafe(32)
        self.expires_at = clock() + TOKEN_TTL_SECONDS
        self.state = "open"
        self.pending = None
        self.submit_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._closed = False
        self.server = _make_server(self)
        self.server_address = self.server.server_address
        self.port = self.server_address[1]
        self.url = f"http://{HOST}:{self.port}/?t={self.token}"
        self._thread = threading.Thread(
            target=self.server.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True
        )
        self._thread.start()
        self._timer = threading.Timer(TOKEN_TTL_SECONDS + 1, self.is_open)
        self._timer.daemon = True
        self._timer.start()

    def is_open(self) -> bool:
        if self.state == "open" and clock() >= self.expires_at:
            self.finish("expired")
        return self.state == "open"

    def check_token(self, token: str) -> bool:
        if not self.is_open() or not token:
            return False
        return secrets.compare_digest(token.encode("utf-8"), self.token.encode("utf-8"))

    def finish(self, state: str) -> None:
        with self._state_lock:
            if self.state != "open":
                return
            self.state = state
            self.pending = None
        threading.Thread(target=self._shutdown, daemon=True).start()

    def close(self) -> None:
        with self._state_lock:
            if self.state == "open":
                self.state = "closed"
                self.pending = None
        self._shutdown()

    def _shutdown(self) -> None:
        with self._state_lock:
            if self._closed:
                return
            self._closed = True
        self._timer.cancel()
        self.server.shutdown()
        self.server.server_close()


class _SetupServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False
    allow_reuse_address = False


class _Handler(BaseHTTPRequestHandler):
    server_version = "investidor10-setup"
    sys_version = ""

    def log_message(self, format, *args) -> None:
        return

    @property
    def session(self) -> SetupSession:
        return self.server.session

    def _send(self, status: int, body: str, nonce: str) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", _csp(nonce))
        self.send_header("X-Content-Type-Options", "nosniff")
        # no-referrer would make browsers send "Origin: null" on the form POST
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(data)

    def _refuse(self, status: int, result: str, text: str) -> None:
        nonce = secrets.token_urlsafe(16)
        self._send(status, _layout(result, _notice("error", text), nonce), nonce)

    def _host_ok(self) -> bool:
        return self.headers.get("Host", "") == f"{HOST}:{self.session.port}"

    def _origin_ok(self) -> bool:
        return self.headers.get("Origin", "") == f"http://{HOST}:{self.session.port}"

    def _expired(self) -> bool:
        if self.session.is_open():
            return False
        self._refuse(
            410,
            "expired",
            "Esta página venceu ou já foi usada. Peça ao assistente para abrir a "
            "configuração de novo.",
        )
        return True

    def do_GET(self) -> None:
        parts = urlsplit(self.path)
        if parts.path != "/" or not self._host_ok():
            self._refuse(403, "forbidden", "Acesso recusado.")
            return
        if self._expired():
            return
        token = parse_qs(parts.query).get("t", [""])[0]
        if not self.session.check_token(token):
            self._refuse(
                403,
                "forbidden",
                "Acesso recusado: abra a página pelo endereço que o assistente abriu.",
            )
            return
        nonce = secrets.token_urlsafe(16)
        current, _ = _current_config()
        body = _layout("form", _form(self.session, current, nonce), nonce, script=True)
        self._send(200, body, nonce)

    def do_POST(self) -> None:
        raw_length = self.headers.get("Content-Length", "")
        if not raw_length.isdigit():
            self._refuse(411, "forbidden", "Envio inválido.")
            return
        length = int(raw_length)
        if length > MAX_BODY_BYTES:
            if length <= MAX_DISCARD_BYTES:
                self.rfile.read(length)
            self._refuse(413, "forbidden", "Envio grande demais.")
            return
        body = self.rfile.read(length)
        if urlsplit(self.path).path != "/" or not (
            self._host_ok() and self._origin_ok()
        ):
            self._refuse(403, "forbidden", "Acesso recusado.")
            return
        if self._expired():
            return
        fields = parse_qs(body.decode("utf-8", "replace"), keep_blank_values=True)
        token = fields.get("token", [""])[0]
        if not self.session.check_token(token):
            self._refuse(403, "forbidden", "Acesso recusado.")
            return
        nonce = secrets.token_urlsafe(16)
        with self.session.submit_lock:
            result, content, script = _submit(self.session, fields, nonce)
        self._send(200, _layout(result, content, nonce, script=script), nonce)


def _make_server(session: SetupSession) -> _SetupServer:
    server = _SetupServer((HOST, 0), _Handler)
    server.session = session
    return server


def _current_config():
    try:
        return wallet_config.read_config(wallet_config.config_path(Path.home())), None
    except wallet_config.ConfigProblem as problem:
        return None, problem.reason


def _first(fields: dict, name: str) -> str:
    return fields.get(name, [""])[0]


def _summary(link, mask: bool) -> str:
    state = "ligado" if mask else "desligado"
    warning = (
        f'<p class="warn" data-warning="public">{html.escape(PUBLIC_WARNING)}</p>'
        if link.mode == "public"
        else ""
    )
    return (
        "<p>Configuração salva.</p><ul>"
        f"<li>Carteira: {_masked(link.wallet_id)}</li>"
        f"<li>Tipo: {_mode_label(link.mode)}</li>"
        f"<li>Modo privacidade: {state}</li></ul>{warning}"
        "<p>Pode fechar esta página e voltar à conversa: diga ao assistente que "
        "salvou.</p>"
    )


def _save(session: SetupSession, link, mask: bool, nonce: str, current):
    config = wallet_config.LocalConfig(
        wallet_id=link.wallet_id,
        share_hash=link.share_hash,
        mode=link.mode,
        mask_values=mask,
        validated_at=datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        source="setup_page",
    )
    try:
        wallet_config.write_config(Path.home(), config)
    except OSError as exc:
        cause = exc.strerror or "erro desconhecido"
        notice = _notice(
            "error",
            f"Não foi possível gravar a configuração neste computador ({cause}). "
            f"Nada foi salvo. Como alternativa, rode no terminal: {TERMINAL_ALTERNATIVE}",
        )
        return "save_failed", _form(session, current, nonce, notice), True
    session.finish("saved")
    return "saved", _summary(link, mask), False


def _submit(session: SetupSession, fields: dict, nonce: str):
    current, problem = _current_config()
    if _first(fields, "action") == "confirm":
        if session.pending is None:
            notice = _notice("error", "Nada para confirmar. " + VALID_FORMS)
            return "invalid_link", _form(session, current, nonce, notice), True
        link, mask = session.pending
        return _save(session, link, mask, nonce, current)
    session.pending = None
    mask = _first(fields, "mask") == "on"
    try:
        link = wallet_config.parse_link(_first(fields, "link"))
    except wallet_config.LinkError as exc:
        notice = _notice("error", str(exc))
        return "invalid_link", _form(session, current, nonce, notice), True
    if problem == "future_version":
        notice = _notice(
            "error",
            "A configuração deste computador foi criada por uma versão mais nova do "
            "produto e não será alterada. Atualize o mcp-investidor10-wallet.",
        )
        return "future_version", notice, False
    result = asyncio.run(wallet_client.check_wallet(link.wallet_id, link.share_hash))
    if result != "valid":
        texts = {
            "access_denied": (
                "O Investidor10 recusou o acesso à carteira. Se ela for restrita, o "
                "link pode estar incompleto ou ter sido renovado: copie de novo o link "
                "de compartilhamento no site. Se for privada, torne-a pública ou "
                "restrita nas configurações do Investidor10. Nada foi salvo."
            ),
            "not_found": (
                "Carteira não encontrada. Confira o link ou o número da carteira. "
                "Nada foi salvo."
            ),
            "unavailable": (
                "O Investidor10 não respondeu agora. Nada foi salvo; tente de novo em "
                "alguns minutos."
            ),
        }
        notice = _notice("error", texts[result])
        return result, _form(session, current, nonce, notice), True
    if current is not None and current.wallet_id != link.wallet_id:
        session.pending = (link, mask)
        content = (
            f"<p>A carteira informada ({_masked(link.wallet_id)}) é diferente da "
            f"configurada ({_masked(current.wallet_id)}). A memória (teses, regras, "
            "decisões e alertas) foi escrita para a carteira atual e continuará "
            "valendo para a nova.</p>"
            '<form method="post" action="/">'
            f'<input type="hidden" name="token" value="{html.escape(session.token)}">'
            '<input type="hidden" name="action" value="confirm">'
            '<button type="submit">Trocar de carteira</button></form>'
            f'<p><a href="/?t={html.escape(session.token)}">Cancelar</a></p>'
        )
        return "confirm_switch", content, False
    if current is not None and (
        current.share_hash,
        current.mode,
        current.mask_values,
    ) == (link.share_hash, link.mode, mask):
        return (
            "unchanged",
            "<p>Nada mudou: a configuração já é esta. Pode voltar à conversa.</p>",
            False,
        )
    return _save(session, link, mask, nonce, current)


_lock = threading.Lock()
_session: SetupSession | None = None


def current_session() -> SetupSession | None:
    return _session


def _launch(url: str) -> bool:
    try:
        return bool(webbrowser.open(url))
    except (webbrowser.Error, OSError):
        return False


def open_setup() -> dict:
    global _session
    with _lock:
        status = "already_open"
        if _session is None or not _session.is_open():
            if _session is not None:
                _session.close()
            try:
                _session = SetupSession()
            except OSError as exc:
                _session = None
                raise SetupUnavailable(str(exc)) from exc
            status = "opened"
        session = _session
    if not _launch(session.url):
        return {
            "status": "open_manually",
            "setup_url": session.url,
            "terminal_alternative": TERMINAL_ALTERNATIVE,
            "message": OPEN_MANUALLY_MESSAGE,
        }
    message = OPENED_MESSAGE if status == "opened" else ALREADY_OPEN_MESSAGE
    return {"status": status, "message": message}


def close() -> None:
    global _session
    with _lock:
        if _session is not None:
            _session.close()
        _session = None
