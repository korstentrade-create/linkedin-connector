"""OAuth 2.0 login (run once) and per-user token storage."""
import json
import os
import secrets
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

SCOPES = "openid profile w_member_social"
HOME = Path(os.getenv("LINKEDIN_HOME", Path.home() / ".linkedin-connector")).expanduser()
TOKENS = HOME / "tokens"  # one file per member id, so multi-user is a small step later


def _env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise SystemExit(f"Missing environment variable {name}")
    return v


def save_token(member_id: str, data: dict) -> Path:
    TOKENS.mkdir(parents=True, exist_ok=True)
    data["expires_at"] = int(time.time()) + int(data.get("expires_in", 0))
    p = TOKENS / f"{member_id}.json"
    p.write_text(json.dumps(data))
    p.chmod(0o600)
    return p


def load_token(member_id: str | None = None) -> dict | None:
    """Return the token for member_id, or the only stored token if there is exactly one."""
    if not TOKENS.exists():
        return None
    files = [TOKENS / f"{member_id}.json"] if member_id else sorted(TOKENS.glob("*.json"))
    if len(files) != 1 or not files[0].exists():
        return None
    d = json.loads(files[0].read_text())
    d["member_id"] = files[0].stem
    return d


def main() -> None:
    client_id, secret = _env("LINKEDIN_CLIENT_ID"), _env("LINKEDIN_CLIENT_SECRET")
    redirect = os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:8765/callback")
    state = secrets.token_urlsafe(16)
    got: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            q = parse_qs(urlparse(self.path).query)
            got.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"LinkedIn connected. You can close this tab.")

        def log_message(self, *a):
            pass

    url = "https://www.linkedin.com/oauth/v2/authorization?" + urlencode({
        "response_type": "code", "client_id": client_id,
        "redirect_uri": redirect, "state": state, "scope": SCOPES})
    print("Opening browser to authorize...\n", url)
    webbrowser.open(url)
    HTTPServer(("localhost", urlparse(redirect).port or 8765), Handler).handle_request()

    if got.get("state") != state or "code" not in got:
        raise SystemExit(f"Authorization failed: {got}")
    r = httpx.post("https://www.linkedin.com/oauth/v2/accessToken", data={
        "grant_type": "authorization_code", "code": got["code"],
        "redirect_uri": redirect, "client_id": client_id, "client_secret": secret})
    r.raise_for_status()
    tok = r.json()
    me = httpx.get("https://api.linkedin.com/v2/userinfo",
                   headers={"Authorization": f"Bearer {tok['access_token']}"})
    me.raise_for_status()
    path = save_token(me.json()["sub"], tok)
    print(f"Saved token for {me.json().get('name', 'member')} at {path}")


if __name__ == "__main__":
    main()
