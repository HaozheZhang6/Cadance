"""Post UA-24 progress updates to Discord.

Reads $DISCORD_WEBHOOK from .env (or env). Falls back to writing
tmp/discord_progress.log if the webhook is missing.

Used as: `discord_progress.py "msg here"` or imported via `post(msg)`.
"""

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "tmp" / "discord_progress.log"


def _load_env():
    env_path = ROOT / ".env"
    if env_path.exists():
        try:
            from dotenv import load_dotenv

            load_dotenv(env_path, override=False)
        except ImportError:
            pass


def post(msg: str) -> bool:
    """Post msg to Discord webhook. Returns True on success, False otherwise.

    Always appends to local log file as a backup.
    """
    _load_env()
    LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG, "a") as f:
        f.write(f"[{ts}] {msg}\n")

    url = os.environ.get("DISCORD_WEBHOOK_URL") or os.environ.get("DISCORD_WEBHOOK")
    if not url:
        print(f"[{ts}] (no DISCORD_WEBHOOK set, logged only) {msg}")
        return False

    try:
        import requests

        r = requests.post(url, json={"content": msg[:1900]}, timeout=10)
        ok = r.status_code in (200, 204)
        print(f"[{ts}] discord status={r.status_code} ok={ok}")
        return ok
    except Exception as e:
        print(f"[{ts}] discord ERR {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "(empty)"
    post(msg)
