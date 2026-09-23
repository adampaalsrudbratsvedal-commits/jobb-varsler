"""Stier og innstillinger for jobbvarsleren."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("JOBBVARSLER_DATA", ROOT / "data"))

# OAuth-klienten du laster ned fra Google Cloud Console, og tokenet innloggingen lagrer.
CREDENTIALS_FILE = DATA_DIR / "credentials.json"
TOKEN_FILE = DATA_DIR / "token.json"
STATE_FILE = DATA_DIR / "state.json"
LOG_FILE = DATA_DIR / "jobbvarsler.log"
DASHBOARD_FILE = DATA_DIR / "oversikt.html"

MODEL = "claude-opus-5"

# Første kjøring ser så langt tilbake; senere kjøringer starter der forrige slapp.
FIRST_RUN_LOOKBACK_DAYS = 3
MAX_MESSAGES_PER_RUN = 200
# Ved gjennomgang bakover i tid spør vi Gmail bare etter e-poster med disse ordene,
# så vi slipper å laste ned hele innboksen. Gmail matcher hele ord, derfor bøyningene.
SCAN_QUERY = (
    "{søknad søknaden søknader søkt søker stilling stillingen intervju rekruttering kandidat "
    "application applied applying interview candidate position recruitment offer}"
)
MAX_SCAN_MESSAGES = 1000
# ATS-e-poster er korte; taket hindrer at lange nyhetsbrev blir dyre å klassifisere.
MAX_BODY_CHARS = 15_000
# Hvor lenge vi husker hvilke e-poster som allerede er vurdert.
PROCESSED_RETENTION_DAYS = 90

# Kategorier som gir Windows-varsel. "mottatt" lagres fortsatt og vises via MCP.
NOTIFY_CATEGORIES = {"intervju", "tilbud", "avslag", "neste_steg", "annet"}

# Billig forfilter før Claude. Delord fanger bøyninger ("søknaden", "stillingen").
KEYWORDS = (
    # norsk
    "søknad", "søker", "stilling", "intervju", "rekrutter", "kandidat",
    "jobbtilbud", "tilbud om ansettelse", "arbeidskontrakt", "ansettelse",
    "neste steg", "videre prosess", "gå videre med", "dessverre", "referanse",
    "case-oppgave", "caseoppgave", "personlighetstest", "sommerjobb",
    "trainee", "internship", "graduate",
    # engelsk
    "application", "applied", "interview", "recruit", "candidate",
    "job offer", "offer letter", "position", "hiring", "talent acquisition",
    "next steps", "unfortunately", "assessment", "coding challenge",
    # vanlige rekrutteringssystemer (ATS)
    "teamtailor", "webcruiter", "jobylon", "workday", "greenhouse",
    "lever.co", "smartrecruiters", "hr-manager", "varbi", "recman",
    "reachmee", "successfactors", "talentech", "easycruit",
)
