"""Grupperer funn til søknader per bedrift, med status og tidslinje."""

import re
from email.utils import parseaddr

# Rekrutteringssystemer og generiske avsendere som ikke sier hvilken bedrift det gjelder.
PLATFORMS = {
    "workable", "workablemail", "teamtailor", "webcruiter", "webcruitermail", "jobylon",
    "workday", "myworkday", "greenhouse", "lever", "smartrecruiters", "hr-manager",
    "hrmanager", "recruitee", "reachmee", "varbi", "recman", "homerun", "talentadore",
    "jobs2web", "successfactors", "easycruit", "talentech", "linkedin", "gmail",
    "outlook", "hotmail",
}
GENERIC_LOCALPARTS = {
    "noreply", "no-reply", "donotreply", "do-not-reply", "notifications", "recruiting",
    "recruitment", "rekruttering", "careers", "jobs", "jobb", "hr", "talent", "post",
    "candidates", "info",
}
NAME_NOISE = re.compile(
    r"\((do not reply|ikke svar)\)|\b(recruiting|recruitment|rekruttering|careers|talent acquisition)\b",
    re.IGNORECASE,
)
SUBJECT_COMPANY = re.compile(
    r"\b(?:to|at|til|hos)\s+([A-ZÆØÅ0-9][\w&.'\- ]{1,40}?)\s*(?:[!.,:\-–|(]|$)"
)
NOT_A_COMPANY = re.compile(r"^(stillingen|the position|the role|our|vår|oss|deg|you)\b", re.IGNORECASE)


def company_of(finding: dict) -> str:
    return _tidy(_raw_company(finding))


def _tidy(name: str) -> str:
    """Fjerner selskapsform og parentes: "Computas (Norge) AS" -> "Computas"."""
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name.strip())
    return re.sub(r"\s+(AS|ASA|AB|Ltd\.?|Inc\.?|GmbH)$", "", name, flags=re.IGNORECASE).strip() or name


def _raw_company(finding: dict) -> str:
    if finding.get("company"):
        return finding["company"].strip()

    match = SUBJECT_COMPANY.search(finding.get("subject", ""))
    if match and not NOT_A_COMPANY.match(match.group(1)):
        return match.group(1).strip()

    name, addr = parseaddr(finding.get("sender", ""))
    name = "" if "@" in name else name.strip().strip('"')
    if " - " in name:
        return name.rsplit(" - ", 1)[1].strip()
    if "/" in name:
        return name.split("/", 1)[0].strip()
    name = NAME_NOISE.sub("", name).strip(" -")

    local, _, domain = addr.lower().partition("@")
    labels = [l for l in domain.split(".") if l]
    root = labels[-2] if len(labels) >= 2 else ""
    platform = root in PLATFORMS or any(l in PLATFORMS for l in labels)

    if name and name.lower() not in PLATFORMS:
        # Navn som inneholder domenet ("DNB" / dnb.no) er bedriftsnavnet; ellers er det
        # trolig en person, og da sier domenet mer (jorgen@geomatikk.no -> Geomatikk).
        if platform or root.replace("-", "") in name.lower().replace(" ", ""):
            return name
    if root and not platform:
        return root.replace("-", " ").title()
    if local and local not in GENERIC_LOCALPARTS:
        return local.replace(".", " ").title()  # f.eks. if@myworkday.com -> If
    return name or "Ukjent bedrift"


def _key(company: str) -> str:
    key = re.sub(r"\b(as|asa|ab|ltd|inc|gmbh)\b", "", company.lower())
    return re.sub(r"[^a-z0-9æøå]", "", key) or company.lower()


def apply_overrides(findings: list[dict], overrides: dict) -> list[dict]:
    result = []
    for f in findings:
        o = overrides.get(f["id"], {})
        if o.get("hidden"):
            continue
        f = {**f, **{k: v for k, v in o.items() if k in ("company", "category") and v}}
        f["company"] = company_of(f)
        result.append(f)
    return result


def build_applications(findings: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for f in findings:
        groups.setdefault(_key(f["company"]), []).append(f)

    apps = []
    for events in groups.values():
        events.sort(key=lambda f: f["received_ts"])
        answers = [e for e in events if e["category"] not in ("mottatt", "annet")]
        status = answers[-1]["category"] if answers else "mottatt"
        apps.append({
            "company": events[-1]["company"],
            "status": status,
            "roles": sorted({e["role"] for e in events if e.get("role")}),
            "applied_ts": events[0]["received_ts"],
            "updated_ts": events[-1]["received_ts"],
            "events": events,
        })
    apps.sort(key=lambda a: a["updated_ts"], reverse=True)
    return apps
