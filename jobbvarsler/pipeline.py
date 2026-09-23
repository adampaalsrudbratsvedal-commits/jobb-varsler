"""Felles flyt for bakgrunnsjobben og MCP-serveren: hent nye e-poster, vurder dem, lagre funn."""

import logging
import time
from datetime import datetime
from email.utils import parseaddr

import anthropic

from . import gmail
from .classifier import classify, looks_job_related, make_client
from .config import FIRST_RUN_LOOKBACK_DAYS, MAX_MESSAGES_PER_RUN
from .notify import notify_findings
from .rules import categorize
from .store import load_state, save_state

log = logging.getLogger(__name__)

# Overlapp mot forrige sjekk, i tilfelle Gmail indekserer e-poster litt forsinket.
OVERLAP_SECONDS = 600


def check_new(notify: bool, lookback_days: int | None = None) -> list[dict]:
    """Vurderer e-poster som ikke er sett før og returnerer nye jobbrelaterte funn."""
    state = load_state()
    now = int(time.time())
    if lookback_days is not None:
        after = now - lookback_days * 86400
    elif state["last_check"]:
        after = state["last_check"] - OVERLAP_SECONDS
    else:
        after = now - FIRST_RUN_LOOKBACK_DAYS * 86400

    service = gmail.get_service()
    ids = gmail.list_message_ids(service, after, MAX_MESSAGES_PER_RUN)
    if len(ids) >= MAX_MESSAGES_PER_RUN:
        log.warning("Traff grensen på %d e-poster; eldre e-poster i vinduet ble hoppet over.", len(ids))

    client = make_client()
    claude_paused = False
    retry_from: int | None = None
    new_findings: list[dict] = []

    try:
        for msg_id in ids:
            if msg_id in state["processed"]:
                continue
            email = gmail.get_email(service, msg_id)
            if not looks_job_related(email):
                state["processed"][msg_id] = email.timestamp
                continue

            if client is None:
                finding = _rule_finding(email)
            elif claude_paused:
                retry_from = min(retry_from or email.timestamp, email.timestamp)
                continue
            else:
                try:
                    assessment = classify(client, email)
                except anthropic.AuthenticationError as exc:
                    log.error("Claude-nøkkelen ble avvist (%s); bruker regler i stedet.", exc)
                    client = None
                    finding = _rule_finding(email)
                except (anthropic.RateLimitError, anthropic.APIConnectionError) as exc:
                    log.warning("Claude utilgjengelig (%s); prøver igjen neste kjøring.", exc)
                    claude_paused = True
                    retry_from = min(retry_from or email.timestamp, email.timestamp)
                    continue
                except anthropic.APIStatusError as exc:
                    if exc.status_code >= 500:
                        log.warning("Claude-feil %s; prøver igjen neste kjøring.", exc.status_code)
                        claude_paused = True
                        retry_from = min(retry_from or email.timestamp, email.timestamp)
                        continue
                    log.error("Claude avviste forespørselen for %s: %s", msg_id, exc)
                    finding = _rule_finding(email)
                else:
                    if assessment is None or not assessment.is_job_feedback:
                        finding = None
                    else:
                        finding = _finding(email, verified=True, assessment=assessment)

            state["processed"][msg_id] = email.timestamp
            if finding is None:
                continue
            state["findings"].append(finding)
            new_findings.append(finding)
    finally:
        # Et vanlig vindu flytter "sist sjekket" framover; et manuelt bakovervindu gjør det ikke.
        if lookback_days is None:
            state["last_check"] = retry_from - 60 if retry_from else now
        save_state(state)

    new_findings.sort(key=lambda f: f["received"])
    if notify:
        notify_findings(new_findings)
    return new_findings


def recent_findings(days: int) -> list[dict]:
    cutoff = datetime.now().timestamp() - days * 86400
    findings = [f for f in load_state()["findings"] if f["received_ts"] >= cutoff]
    return sorted(findings, key=lambda f: f["received_ts"], reverse=True)


def _rule_finding(email: gmail.Email) -> dict | None:
    category = categorize(email)
    return _finding(email, verified=False, category=category) if category else None


def _finding(email: gmail.Email, verified: bool, assessment=None, category: str = "annet") -> dict:
    sender_name, sender_addr = parseaddr(email.sender)
    return {
        "id": email.id,
        "url": email.url,
        "received": datetime.fromtimestamp(email.timestamp).isoformat(timespec="minutes"),
        "received_ts": email.timestamp,
        "sender": email.sender,
        "sender_name": sender_name or sender_addr,
        "subject": email.subject,
        "category": assessment.category if assessment else category,
        "company": assessment.company if assessment else "",
        "role": assessment.role if assessment else "",
        "summary": assessment.summary if assessment else email.subject,
        "snippet": email.snippet[:300],
        # False = sortert med gratis regler, ikke bekreftet av Claude.
        "verified": verified,
    }
