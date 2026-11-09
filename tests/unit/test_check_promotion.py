import http.server
import io
import json
import socket
import subprocess
import sys
import threading
import zipfile
from pathlib import Path
from typing import ClassVar

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_promotion.py"
VERSION = "0.4.0"
MANIFESTS = [
    "plugin/.claude-plugin/plugin.json",
    "plugin/.codex-plugin/plugin.json",
    "plugin/.devin-plugin/plugin.json",
    "plugin/gemini-extension.json",
]
BUNDLE = "plugin/servers/carteira.mcpb"

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="git on PATH and POSIX paths"
)


def _git(cwd, *args):
    result = subprocess.run(
        [
            "git",
            "-c", "user.email=t@t",
            "-c", "user.name=t",
            "-c", "commit.gpgsign=false",
            "-c", "tag.gpgsign=false",
            *args,
        ],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )  # fmt: skip
    return result.stdout.strip()


def _write_manifest(root, relative, version):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"name": "x", "version": version}), encoding="utf-8")


def _write_bundle(root, version):
    path = root / BUNDLE
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("manifest.json", json.dumps({"version": version}))
    path.write_bytes(buffer.getvalue())


def _commit(root, message):
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)
    return _git(root, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "develop")
    for relative in MANIFESTS:
        _write_manifest(root, relative, VERSION)
    sha = _commit(root, "release")
    _git(root, "tag", "-a", f"v{VERSION}", "-m", "release")
    return root, sha


class _Index(http.server.BaseHTTPRequestHandler):
    published: ClassVar[set[str]] = {VERSION}

    def do_GET(self):
        parts = self.path.strip("/").split("/")
        found = (
            len(parts) == 4
            and parts[:2] == ["pypi", "mcp-investidor10-wallet"]
            and parts[2] in self.published
            and parts[3] == "json"
        )
        body = b"{}" if found else b"not found"
        self.send_response(200 if found else 404)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def index_url():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Index)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


@pytest.fixture
def dead_index_url():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    return f"http://127.0.0.1:{port}"


def _run(root, ref, sha, url):
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--head-ref", ref,
            "--head-sha", sha,
            "--repo-root", str(root),
            "--index-url", url,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )  # fmt: skip


def test_accepts_promotion_of_a_published_final_version(repo, index_url):
    root, sha = repo
    result = _run(root, f"promote/v{VERSION}", sha, index_url)
    assert result.returncode == 0, result.stderr


def test_accepts_bundled_server_manifest_with_same_version(repo, index_url):
    root, _ = repo
    _write_bundle(root, VERSION)
    sha = _commit(root, "bundle")
    _git(root, "tag", "-f", "-a", f"v{VERSION}", "-m", "release")
    result = _run(root, f"promote/v{VERSION}", sha, index_url)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "ref",
    [
        "develop",
        "main",
        "hotfix/0.4.1",
        "feature/promote/v0.4.0",
        "promote/v0.4.0rc1",
        "promote/v0.4.0-rc.1",
        "promote/v0.4",
        "promote/0.4.0",
        "promote/v0.4.0/extra",
    ],
)
def test_rejects_head_ref_that_is_not_a_final_promotion(repo, index_url, ref):
    root, sha = repo
    result = _run(root, ref, sha, index_url)
    assert result.returncode == 1
    assert "promote/vX.Y.Z" in result.stderr


def test_rejects_commit_different_from_the_tag(repo, index_url):
    root, _ = repo
    (root / "extra.txt").write_text("x", encoding="utf-8")
    other = _commit(root, "after the tag")
    result = _run(root, f"promote/v{VERSION}", other, index_url)
    assert result.returncode == 1
    assert "commit" in result.stderr


def test_rejects_when_the_tag_does_not_exist(repo, index_url):
    root, sha = repo
    result = _run(root, "promote/v0.5.0", sha, index_url)
    assert result.returncode == 1
    assert "v0.5.0" in result.stderr


@pytest.mark.parametrize("relative", MANIFESTS)
def test_rejects_manifest_with_another_version(repo, index_url, relative):
    root, _ = repo
    _write_manifest(root, relative, "0.3.0")
    sha = _commit(root, "drift")
    _git(root, "tag", "-f", "-a", f"v{VERSION}", "-m", "release")
    result = _run(root, f"promote/v{VERSION}", sha, index_url)
    assert result.returncode == 1
    assert relative in result.stderr


def test_rejects_bundled_server_manifest_with_another_version(repo, index_url):
    root, _ = repo
    _write_bundle(root, "0.3.0")
    sha = _commit(root, "bundle drift")
    _git(root, "tag", "-f", "-a", f"v{VERSION}", "-m", "release")
    result = _run(root, f"promote/v{VERSION}", sha, index_url)
    assert result.returncode == 1
    assert BUNDLE in result.stderr


def test_rejects_version_missing_from_the_index(repo, index_url):
    root, sha = repo
    _Index.published = set()
    try:
        result = _run(root, f"promote/v{VERSION}", sha, index_url)
    finally:
        _Index.published = {VERSION}
    assert result.returncode == 1
    assert "índice" in result.stderr


def test_fails_closed_when_the_index_is_unreachable(repo, dead_index_url):
    root, sha = repo
    result = _run(root, f"promote/v{VERSION}", sha, dead_index_url)
    assert result.returncode == 1
    assert "índice" in result.stderr
