import secrets
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from app.core.config import settings

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = BACKEND_ROOT / ".env"
REDIRECT_URI = "http://localhost:8765/oauth2callback"
SCOPES = (
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
)
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    expected_state = ""
    result: dict[str, str] | None = None

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        state = params.get("state", [""])[0]
        if parsed.path != "/oauth2callback" or state != self.expected_state:
            self.send_error(400, "Invalid OAuth callback.")
            return

        error = params.get("error", [""])[0]
        code = params.get("code", [""])[0]
        if error:
            type(self).result = {"error": error}
            body = b"Google authorization was not completed. You can close this tab."
        elif code:
            type(self).result = {"code": code}
            body = b"Google authorization received. You can close this tab."
        else:
            type(self).result = {"error": "missing_code"}
            body = b"Google did not return an authorization code. You can close this tab."

        self.send_response(200 if code and not error else 400)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        return


def _replace_refresh_token(refresh_token: str) -> None:
    content = ENV_PATH.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)
    replacement = f"GMAIL_REFRESH_TOKEN={refresh_token}"
    for index, line in enumerate(lines):
        if line.lstrip().startswith("GMAIL_REFRESH_TOKEN="):
            ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
            lines[index] = replacement + ending
            break
    else:
        ending = "" if not content or content.endswith(("\n", "\r")) else "\n"
        lines.append(f"{ending}{replacement}\n")

    temp_path = ENV_PATH.with_name(f"{ENV_PATH.name}.tmp")
    temp_path.write_text("".join(lines), encoding="utf-8")
    temp_path.replace(ENV_PATH)


def main() -> None:
    client_id = settings.GMAIL_CLIENT_ID
    client_secret = settings.GMAIL_CLIENT_SECRET
    if not client_id or not client_secret:
        raise RuntimeError("Gmail OAuth client ID and secret must be configured.")
    if not ENV_PATH.is_file():
        raise RuntimeError(f"Backend environment file was not found: {ENV_PATH}")

    state = secrets.token_urlsafe(32)
    OAuthCallbackHandler.expected_state = state
    OAuthCallbackHandler.result = None
    authorization_params = {
        'client_id': client_id,
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'scope': ' '.join(SCOPES),
        'access_type': 'offline',
        'prompt': 'consent',
        'include_granted_scopes': 'true',
        'state': state,
    }
    authorization_url = f"{AUTH_URL}?{urlencode(authorization_params)}"

    server = HTTPServer(("127.0.0.1", 8765), OAuthCallbackHandler)
    server.timeout = 300
    print("Open this authorization URL while signed in as the Gmail sending account:")
    print(authorization_url, flush=True)
    print("Waiting up to five minutes for Google's callback...", flush=True)
    try:
        while OAuthCallbackHandler.result is None:
            server.handle_request()
    finally:
        server.server_close()

    result = OAuthCallbackHandler.result
    if result is None or "error" in result:
        error = result.get("error", "unknown") if result else "timeout"
        raise RuntimeError(f"Google authorization did not complete ({error}).")

    token_response = httpx.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": result["code"],
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=20,
    )
    if token_response.status_code != 200:
        raise RuntimeError(
            f"Google rejected the authorization-code exchange "
            f"(HTTP {token_response.status_code})."
        )

    payload = token_response.json()
    refresh_token = payload.get("refresh_token")
    scope_value = payload.get("scope", "")
    granted_scopes = set(scope_value.split()) if isinstance(scope_value, str) else set()
    if not isinstance(refresh_token, str) or not refresh_token:
        raise RuntimeError(
            "Google returned no refresh token. Revoke prior Komsan access for "
            "the sending account and run authorization again."
        )
    if not set(SCOPES).issubset(granted_scopes):
        raise RuntimeError(
            "Google did not grant both required Gmail scopes; the existing "
            "refresh token was not changed."
        )

    _replace_refresh_token(refresh_token)
    print("Gmail authorization succeeded; the backend .env refresh token was updated.")
    print("Restart the backend before sending or verifying Gmail messages.")


if __name__ == "__main__":
    main()
