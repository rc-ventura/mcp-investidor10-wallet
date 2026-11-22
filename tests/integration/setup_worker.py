import json
import sys
import time
import webbrowser

from investidor10_wallet import setup_page, wallet_client


async def _valid(wallet_id, share_hash=None, *args, **kwargs):
    return "valid"


def main():
    webbrowser.open = lambda *a, **k: False
    wallet_client.check_wallet = _valid
    result = setup_page.open_setup()
    print(json.dumps({"setup_url": result["setup_url"]}), flush=True)
    deadline = time.monotonic() + 60
    session = setup_page.current_session()
    while session.state == "open" and time.monotonic() < deadline:
        time.sleep(0.05)
    print(json.dumps({"state": session.state}), flush=True)
    return 0 if session.state == "saved" else 1


if __name__ == "__main__":
    sys.exit(main())
