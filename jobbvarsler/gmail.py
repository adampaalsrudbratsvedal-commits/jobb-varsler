"""Lesetilgang til Gmail via Gmail API (kun gmail.readonly)."""

import base64
import html
import re
from dataclasses import dataclass

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .config import CREDENTIALS_FILE, TOKEN_FILE

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
# Nye forsøk med eksponentiell pause ved fartsgrense (429/403 rateLimitExceeded) og 5xx.
RETRIES = 5


class AuthRequired(RuntimeError):
    """Gmail-tokenet mangler eller er utløpt; brukeren må logge inn på nytt."""


@dataclass
class Email:
    id: str
    thread_id: str
    sender: str
    subject: str
    date: str
    timestamp: int
    snippet: str
    body: str
    is_bulk: bool  # har List-Unsubscribe-header, typisk nyhetsbrev/masseutsendelse

    @property
    def url(self) -> str:
        return f"https://mail.google.com/mail/u/0/#all/{self.thread_id}"


def load_credentials(interactive: bool = False) -> Credentials:
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
            return creds
        except RefreshError:
            if not interactive:
                raise AuthRequired("Gmail-innloggingen er utløpt. Kjør: python login.py")
    if not interactive:
        raise AuthRequired("Ikke logget inn i Gmail ennå. Kjør: python login.py")
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"Fant ikke {CREDENTIALS_FILE}. Last ned OAuth-klienten (Desktop app) "
            "fra Google Cloud Console og lagre den der."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return creds


def get_service(interactive: bool = False):
    return build("gmail", "v1", credentials=load_credentials(interactive), cache_discovery=False)


def list_message_ids(service, after_ts: int, limit: int, extra_query: str = "") -> list[str]:
    """ID-er for mottatte e-poster etter `after_ts` (epoch-sekunder), nyeste først."""
    query = f"after:{after_ts} -in:sent -in:drafts -in:chats -in:spam -in:trash {extra_query}".strip()
    ids: list[str] = []
    page_token = None
    while len(ids) < limit:
        resp = service.users().messages().list(
            userId="me", q=query, maxResults=min(100, limit - len(ids)), pageToken=page_token
        ).execute(num_retries=RETRIES)
        ids.extend(m["id"] for m in resp.get("messages", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return ids


def get_email(service, msg_id: str) -> Email:
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute(num_retries=RETRIES)
    payload = msg.get("payload", {})
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
    return Email(
        id=msg["id"],
        thread_id=msg["threadId"],
        sender=headers.get("from", ""),
        subject=headers.get("subject", ""),
        date=headers.get("date", ""),
        timestamp=int(msg.get("internalDate", 0)) // 1000,
        snippet=html.unescape(msg.get("snippet", "")),
        body=_extract_text(payload),
        is_bulk="list-unsubscribe" in headers,
    )


def get_profile_email(service) -> str:
    return service.users().getProfile(userId="me").execute(num_retries=RETRIES)["emailAddress"]


def _extract_text(payload: dict) -> str:
    plain: list[str] = []
    htmls: list[str] = []
    _walk(payload, plain, htmls)
    if plain:
        return "\n\n".join(plain).strip()
    return "\n\n".join(_html_to_text(h) for h in htmls).strip()


def _walk(part: dict, plain: list[str], htmls: list[str]) -> None:
    mime = part.get("mimeType", "")
    data = part.get("body", {}).get("data")
    if data and mime == "text/plain":
        # Noen rekrutteringssystemer har HTML-koder også i ren tekst ("s&oslash;knad").
        plain.append(html.unescape(_decode(data)))
    elif data and mime == "text/html":
        htmls.append(_decode(data))
    for sub in part.get("parts") or []:
        _walk(sub, plain, htmls)


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="replace")


def _html_to_text(markup: str) -> str:
    text = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", markup)
    text = re.sub(r"(?i)<br\s*/?>|</(p|div|tr|li|h\d)>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()
