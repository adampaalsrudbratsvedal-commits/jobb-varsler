"""Én runde for bakgrunnsjobben: sjekk Gmail og vis Windows-varsel for nye funn."""

import logging

from .config import LOG_FILE
from .gmail import AuthRequired
from .notify import toast
from .pipeline import check_new

log = logging.getLogger("jobbvarsler.poll")


def main() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE, level=logging.INFO, encoding="utf-8",
        format="%(asctime)s [poll] %(levelname)s %(name)s: %(message)s",
    )
    try:
        findings = check_new(notify=True)
        log.info("Ferdig: %d nye funn.", len(findings))
    except AuthRequired as exc:
        log.error(str(exc))
        toast("Jobbvarsler trenger ny innlogging", str(exc))
    except Exception:
        log.exception("Kjøringen feilet")
