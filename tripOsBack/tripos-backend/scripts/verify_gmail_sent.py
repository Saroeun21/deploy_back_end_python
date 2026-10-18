import argparse
from collections.abc import Mapping
from email.utils import getaddresses
import sys

import httpx

from app.core.config import settings

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_MESSAGES_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"


def verify_sent_message(recipient: str, subject: str) -> bool:
    client_id = settings.GMAIL_CLIENT_ID
    client_secret = settings.GMAIL_CLIENT_SECRET
    refresh_token = settings.GMAIL_REFRESH_TOKEN
    if not all((client_id, client_secret, refresh_token)):
        raise RuntimeError(
            "Set GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, and GMAIL_REFRESH_TOKEN."
        )

    token_response = httpx.post(
        GOOGLE_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=15,
    )
    if token_response.status_code != 200:
        raise RuntimeError(
            f"Google OAuth token refresh failed (HTTP {token_response.status_code})."
        )
    token_payload = token_response.json()
    access_token = (
        token_payload.get("access_token")
        if isinstance(token_payload, Mapping)
        else None
    )
    if not isinstance(access_token, str) or not access_token:
        raise RuntimeError("Google OAuth returned no access token.")

    query = f'in:sent to:{recipient} subject:"{subject}"'
    response = httpx.get(
        GMAIL_MESSAGES_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        params={"q": query, "maxResults": 20},
        timeout=15,
    )
    if response.status_code == 403:
        raise RuntimeError(
            "Gmail denied Sent-folder search. Reauthorize the Gmail OAuth "
            "client with both gmail.send and gmail.readonly, then update "
            "GMAIL_REFRESH_TOKEN."
        )
    if response.status_code != 200:
        raise RuntimeError(
            f"Gmail Sent-folder search failed (HTTP {response.status_code})."
        )

    listing = response.json()
    if not isinstance(listing, Mapping):
        raise RuntimeError("Gmail returned an invalid Sent-folder response.")
    messages = listing.get("messages", [])
    if not isinstance(messages, list):
        raise RuntimeError("Gmail returned an invalid Sent-folder message list.")
    for message in messages:
        message_id = message.get("id") if isinstance(message, Mapping) else None
        if not isinstance(message_id, str):
            continue
        message_response = httpx.get(
            f"{GMAIL_MESSAGES_URL}/{message_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "format": "metadata",
                "metadataHeaders": ["To", "Subject"],
            },
            timeout=15,
        )
        if message_response.status_code == 403:
            raise RuntimeError(
                "Gmail denied message verification. Reauthorize the Gmail "
                "OAuth client with both gmail.send and gmail.readonly, then "
                "update GMAIL_REFRESH_TOKEN."
            )
        if message_response.status_code != 200:
            raise RuntimeError(
                "Gmail could not read a matching Sent-folder message "
                f"(HTTP {message_response.status_code})."
            )

        payload = message_response.json()
        if not isinstance(payload, Mapping):
            raise RuntimeError("Gmail returned an invalid message response.")
        message_payload = payload.get("payload")
        headers = (
            message_payload.get("headers", [])
            if isinstance(message_payload, Mapping)
            else []
        )
        if not isinstance(headers, list):
            raise RuntimeError("Gmail returned invalid message headers.")
        values = {
            header.get("name", "").casefold(): header.get("value", "")
            for header in headers
            if isinstance(header, Mapping)
        }
        recipients = {
            address.casefold()
            for _, address in getaddresses([values.get("to", "")])
        }
        if (
            recipient.casefold() in recipients
            and values.get("subject") == subject
        ):
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check whether Gmail has the matching message in Sent."
    )
    parser.add_argument("--to", required=True, help="Expected recipient address")
    parser.add_argument("--subject", required=True, help="Exact email subject")
    args = parser.parse_args()

    try:
        found = verify_sent_message(args.to, args.subject)
    except (httpx.RequestError, ValueError, RuntimeError) as error:
        print(f"Verification failed: {error}", file=sys.stderr)
        return 1

    if found:
        print("Matching email found in the configured Gmail account's Sent folder.")
        print("This verifies sender-side acceptance, not recipient inbox delivery.")
        return 0

    print("No matching email found in the configured Gmail account's Sent folder.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
