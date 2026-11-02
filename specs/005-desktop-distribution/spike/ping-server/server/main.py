import datetime
import html
import http.server
import secrets
import threading
import urllib.parse
import webbrowser
from pathlib import Path

from fastmcp import FastMCP, FastMCPApp
from prefab_ui.actions import ShowToast
from prefab_ui.actions.mcp import CallTool
from prefab_ui.app import PrefabApp
from prefab_ui.components import Button, Column, Form, Heading, Input

SPIKE_DIR = Path.home() / ".investidor10-spike"
PAGE_TIMEOUT_SECONDS = 600

mcp = FastMCP("spike-ping")
form_app = FastMCPApp("spike-form")


def record(name: str, text: str) -> None:
    SPIKE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = datetime.datetime.now().astimezone().isoformat()
    with (SPIKE_DIR / name).open("a", encoding="utf-8") as handle:
        handle.write(f"{stamp} {text}\n")


@mcp.tool
def ping() -> str:
    """Returns pong and records the call in ~/.investidor10-spike/log.txt."""
    record("log.txt", "ping")
    return "pong"


def serve_form() -> tuple[http.server.ThreadingHTTPServer, str]:
    token = secrets.token_urlsafe(16)

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = (
                "<!doctype html><meta charset=utf-8><title>Spike</title>"
                "<form method=post><label>Test value "
                "<input name=value autofocus></label>"
                f"<input type=hidden name=token value={token}>"
                "<button>Send</button></form>"
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            fields = urllib.parse.parse_qs(self.rfile.read(length).decode())
            if fields.get("token", [""])[0] != token:
                self.send_response(403)
                self.end_headers()
                return
            record("valor_pagina.txt", fields.get("value", [""])[0])
            body = html.escape("Saved. You can close this tab.").encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            threading.Thread(target=self.server.shutdown, daemon=True).start()

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    timer = threading.Timer(PAGE_TIMEOUT_SECONDS, server.shutdown)
    timer.daemon = True
    timer.start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/"


@mcp.tool
def abrir_pagina() -> dict:
    """Opens a local form in the default browser; the value goes to a file, not to the chat."""
    _, url = serve_form()
    opened = webbrowser.open(url)
    record("log.txt", f"abrir_pagina opened={opened}")
    if opened:
        return {"status": "opened"}
    return {"status": "open_manually", "setup_url": url}


@form_app.tool()
def salvar_valor_app(value: str) -> str:
    """Saves the value typed in the app form to a file; never echoes it."""
    record("valor_app.txt", value)
    return "saved"


@form_app.ui()
def formulario_app() -> PrefabApp:
    """Opens the same form inside the conversation as an MCP App."""
    with Column(gap=4, css_class="p-6") as view:
        Heading("Spike form")
        with Form(
            on_submit=CallTool(
                "salvar_valor_app",
                on_success=ShowToast("Saved", variant="success"),
                on_error=ShowToast("Failed to save", variant="error"),
            )
        ):
            Input(name="value", label="Test value", required=True)
            Button("Send")
    return PrefabApp(view=view)


mcp.add_provider(form_app)


if __name__ == "__main__":
    mcp.run()
