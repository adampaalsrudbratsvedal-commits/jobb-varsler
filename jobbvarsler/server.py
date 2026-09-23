"""MCP-server som lar Claude sjekke Gmail for jobbrelaterte tilbakemeldinger."""

import logging

from mcp.server.mcpserver import MCPServer

from . import gmail
from .config import LOG_FILE, MAX_BODY_CHARS
from .gmail import AuthRequired
from .pipeline import check_new, recent_findings

mcp = MCPServer(
    "jobb-varsler",
    instructions=(
        "Verktøy for å finne jobbrelaterte tilbakemeldinger (intervju, avslag, tilbud, "
        "neste steg, mottatt søknad) i brukerens Gmail. Funn med verified=false er sortert "
        "med enkle fraseregler og kan ha feil kategori; bruk read_email og vurder selv når "
        "kategorien virker usikker, og rett den i svaret ditt."
    ),
)


@mcp.tool()
def check_job_feedback(notify: bool = False) -> dict:
    """Sjekk Gmail for nye e-poster siden forrige sjekk og returner nye jobbrelaterte tilbakemeldinger.

    Args:
        notify: Vis også Windows-varsel for nye funn.
    """
    try:
        findings = check_new(notify=notify)
    except AuthRequired as exc:
        return {"error": str(exc)}
    return {"new_count": len(findings), "findings": findings}


@mcp.tool()
def list_job_feedback(days: int = 14, category: str | None = None) -> dict:
    """List jobbrelaterte tilbakemeldinger som allerede er funnet, nyeste først. Leser ikke Gmail.

    Args:
        days: Hvor mange dager tilbake.
        category: Filtrer på intervju, tilbud, avslag, neste_steg, mottatt eller annet.
    """
    findings = recent_findings(days)
    if category:
        findings = [f for f in findings if f["category"] == category]
    return {"count": len(findings), "findings": findings}


@mcp.tool()
def scan_job_feedback(days: int = 30) -> dict:
    """Gå gjennom Gmail for de siste `days` dagene (også e-poster fra før verktøyet ble satt opp)
    og returner alle jobbrelaterte tilbakemeldinger i perioden. E-poster som er vurdert før,
    vurderes ikke på nytt.

    Args:
        days: Hvor mange dager tilbake i innboksen (maks 365).
    """
    days = max(1, min(days, 365))
    try:
        check_new(notify=False, lookback_days=days)
    except AuthRequired as exc:
        return {"error": str(exc)}
    findings = recent_findings(days)
    return {"count": len(findings), "findings": findings}


@mcp.tool()
def read_email(message_id: str) -> dict:
    """Les hele teksten i én e-post (id fra funnene), for å vurdere hva svaret faktisk sier.

    Args:
        message_id: `id`-feltet fra et funn.
    """
    try:
        email = gmail.get_email(gmail.get_service(), message_id)
    except AuthRequired as exc:
        return {"error": str(exc)}
    return {
        "from": email.sender,
        "subject": email.subject,
        "date": email.date,
        "url": email.url,
        "body": email.body[:MAX_BODY_CHARS] or email.snippet,
    }


def main() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    # stdout er MCP-kanalen, så logging må gå til fil.
    logging.basicConfig(
        filename=LOG_FILE, level=logging.INFO, encoding="utf-8",
        format="%(asctime)s [server] %(levelname)s %(name)s: %(message)s",
    )
    mcp.run()
