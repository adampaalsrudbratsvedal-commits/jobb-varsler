"""Gratis regelbasert sortering, brukt når ingen Claude-nøkkel er satt opp.

Hver kategori har faste fraser, sjekket i prioritert rekkefølge. E-posten må handle
om en søknad/stilling for å telle i det hele tatt.
"""

import re

from .gmail import Email

# Må finnes et sted i e-posten for at den skal regnes som jobbrelatert.
CONTEXT_WORDS = (
    "søknad", "søker", "stilling", "kandidat", "rekrutter", "intervju", "sommerjobb",
    "internship", "trainee", "application", "applied", "candidate", "position",
    "recruit", "interview", "role",
)

BULK_SUBJECT_WORDS = ("søknad", "søkt", "application", "applying", "applied", "intervju", "interview")

# Typiske jobbvarsler, nettverksinvitasjoner og kontovarsler som ikke er svar på en søknad.
NOISE_PHRASES = (
    "nye jobber", "nye stillinger", "job alert", "jobbvarsel", "jobs you might",
    "stillinger som passer", "i want to connect", "invitations@linkedin",
    "jobnotification", "one-time password", "engangskode", "verification code",
    "verify your", "bekreft e-post", "velkommen til vårt nettverk",
    "thanks for connecting", "talent community", "talent network",
    "welcome / thanks for creating account", "creating account",
)

OFFER = (
    "jobbtilbud", "tilbud om stilling", "tilbud om ansettelse", "arbeidskontrakt",
    "glade for å kunne tilby", "job offer", "offer letter", "pleased to offer",
    "employment contract",
)
# "Dessverre"/"unfortunately" alene er for svakt ("det er dessverre ikke mulig å redigere
# søknaden"), så frasene må si at du ikke går videre.
REJECTION = (
    "dessverre valgt", "har dessverre", "må dessverre", "dessverre ikke nådd",
    "dessverre ikke blitt", "dessverre ikke kommet", "dessverre ikke gå videre",
    "ikke gå videre med din", "ikke gå videre med deg", "ikke nådd opp",
    "gå videre med andre", "gått videre med andre", "gå videre med profiler",
    "gå videre med kandidater som", "valgt andre kandidater",
    "valgt en annen kandidat", "ikke blitt valgt", "ikke blitt med videre",
    "unfortunately we", "unfortunately, we", "move forward with other",
    "moving forward with other", "pursue other candidates", "not be moving forward",
    "not to move forward", "not been selected", "not been successful",
    "regret to inform", "decided to proceed with other", "decided not to proceed",
)
# Må være en faktisk invitasjon til deg. Kvitteringer nevner ofte intervju i fremtid
# ("de mest aktuelle vil bli invitert til intervju"), så generelle ord holder ikke.
INTERVIEW = (
    "vil gjerne invitere deg", "ønsker å invitere deg", "invitere deg til intervju",
    "invitere deg til en", "book et tidspunkt for intervju", "would like to invite you",
    "we'd like to invite you", "we would like to invite you", "invite you to an interview",
    "invite you for an interview", "schedule an interview", "kodeoppgave", "caseoppgave",
    "case-oppgave", "coding challenge", "online assessment", "personlighetstest",
)
INTERVIEW_SUBJECT = ("intervju", "interview")
RECEIPT = (
    "mottatt søknaden", "mottatt din søknad", "søknaden er mottatt", "mottatt søknad",
    "takk for din søknad", "takk for søknaden", "takk for din jobbsøknad",
    "takk for at du søkte", "bekreftelse på søknad", "kjekt at du søker",
    "gøy at du søker", "takk for din interesse", "hører fra oss",
    "thank you for your application", "thanks for your application",
    "thank you for applying", "thanks for applying", "received your application",
    "application has been received", "application was received",
    "thank you for your interest", "you will hear from us",
)
NEXT_STEP = (
    "neste steg", "videre i prosessen", "neste runde", "referansesjekk",
    "next step", "next round", "reference check", "move forward with you",
)


def categorize(email: Email) -> str | None:
    """Kategori for en jobbrelatert tilbakemelding, eller None hvis e-posten ikke er det."""
    subject = email.subject.lower()
    text = f"{email.sender}\n{email.subject}\n{email.snippet}\n{email.body[:8000]}".lower()
    # Linjeskift og hårde mellomrom midt i en frase skal ikke hindre treff.
    text = re.sub(r"\s+", " ", text)

    if any(p in text[:3000] for p in NOISE_PHRASES):
        return None
    if not any(w in text for w in CONTEXT_WORDS):
        return None
    # Nyhetsbrev (har avmeldingslenke) teller bare hvis emnet handler om en søknad.
    if email.is_bulk and not any(w in subject for w in BULK_SUBJECT_WORDS):
        return None

    def has(phrases: tuple[str, ...]) -> bool:
        return any(p in text for p in phrases)

    # Rekkefølgen er prioriteten: et avslag som starter med "takk for din søknad" er et avslag.
    if has(OFFER):
        return "tilbud"
    if has(REJECTION):
        return "avslag"
    if has(INTERVIEW) or any(w in subject for w in INTERVIEW_SUBJECT):
        return "intervju"
    if has(RECEIPT):
        return "mottatt"
    if has(NEXT_STEP):
        return "neste_steg"
    return None
