"""Windows toast-varsler.

E-postinnhold havner aldri i selve PowerShell-kommandoen: toast-XML-en escapes
og sendes base64-kodet, så et ondsinnet emnefelt ikke kan kjøre kode.
"""

import base64
import logging
import subprocess
from xml.sax.saxutils import escape, quoteattr

from .config import NOTIFY_CATEGORIES

log = logging.getLogger(__name__)

# PowerShell sin registrerte AppUserModelID; ukjente ID-er vises ikke pålitelig på Windows 11.
APP_ID = r"{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"
GMAIL_INBOX = "https://mail.google.com/mail/u/0/#inbox"

TITLES = {
    "intervju": "Intervjuinvitasjon",
    "tilbud": "Jobbtilbud!",
    "avslag": "Svar på søknad",
    "neste_steg": "Neste steg i prosessen",
    "mottatt": "Søknad mottatt",
    "annet": "Jobbrelatert e-post",
}

_PS_TEMPLATE = """
$ErrorActionPreference = 'Stop'
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$xml = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{payload}'))
$doc = New-Object Windows.Data.Xml.Dom.XmlDocument
$doc.LoadXml($xml)
$toast = New-Object Windows.UI.Notifications.ToastNotification $doc
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{app_id}').Show($toast)
"""


def toast(title: str, message: str, url: str = GMAIL_INBOX) -> None:
    xml = (
        f"<toast activationType=\"protocol\" launch={quoteattr(url)}>"
        "<visual><binding template=\"ToastGeneric\">"
        f"<text>{escape(title)}</text>"
        f"<text>{escape(message)}</text>"
        "<text placement=\"attribution\">Jobbvarsler</text>"
        "</binding></visual>"
        f"<actions><action content=\"Åpne i Gmail\" activationType=\"protocol\" arguments={quoteattr(url)}/></actions>"
        "<audio src=\"ms-winsoundevent:Notification.Default\"/>"
        "</toast>"
    )
    payload = base64.b64encode(xml.encode("utf-8")).decode("ascii")
    script = _PS_TEMPLATE.replace("{payload}", payload).replace("{app_id}", APP_ID)
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-EncodedCommand", encoded],
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
        timeout=30,
    )
    if result.returncode != 0:
        log.error("Kunne ikke vise varsel: %s", result.stderr.strip())


def notify_findings(findings: list[dict]) -> None:
    findings = [f for f in findings if f["category"] in NOTIFY_CATEGORIES]
    if not findings:
        return
    if len(findings) > 3:
        companies = ", ".join(dict.fromkeys(f["company"] or f["sender_name"] for f in findings))
        toast(f"{len(findings)} nye jobbrelaterte e-poster", companies)
        return
    for f in findings:
        title = TITLES.get(f["category"], TITLES["annet"])
        who = f["company"] or f["sender_name"]
        if who:
            title = f"{title} – {who}"
        toast(title, f["summary"] or f["subject"], f["url"])
