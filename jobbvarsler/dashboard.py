"""Varslingssentralen: en lokal HTML-side med alle søknader og svar.

Siden skrives på nytt etter hver sjekk. Den er helt statisk (ingen server, ingen
nettverkskall), og all e-postdata settes inn som tekst, aldri som HTML.
"""

import json
import time
import webbrowser

from .applications import apply_overrides, build_applications
from .config import DASHBOARD_FILE
from .store import load_state


def write_dashboard() -> None:
    state = load_state()
    findings = apply_overrides(state["findings"], state.get("overrides", {}))
    data = {
        "generated_ts": int(time.time()),
        "last_check_ts": state["last_check"],
        "applications": build_applications(findings),
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    DASHBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_FILE.write_text(_TEMPLATE.replace("__DATA__", payload), encoding="utf-8")


def open_dashboard() -> str:
    write_dashboard()
    webbrowser.open(DASHBOARD_FILE.as_uri())
    return str(DASHBOARD_FILE)


_TEMPLATE = r"""<!doctype html>
<html lang="nb">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Jobbsøknader</title>
<style>
:root {
  --bg: #f6f5f2; --surface: #ffffff; --text: #1d1d1b; --muted: #6b6a66; --border: #e4e2dc;
  --accent: #2f5bd3; --hover: #f1f0ec;
  --wait-bg: #eef0f3; --wait-fg: #4a5361;
  --next-bg: #e6effd; --next-fg: #1f4fb5;
  --int-bg: #f1eafd; --int-fg: #6a3fb8;
  --offer-bg: #e1f4e8; --offer-fg: #1c7a44;
  --rej-bg: #fbeaea; --rej-fg: #a63a3a;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #161615; --surface: #1f1f1d; --text: #ecebe8; --muted: #9b9a95; --border: #33322f;
    --accent: #8ab0ff; --hover: #282826;
    --wait-bg: #2b2d31; --wait-fg: #b8bec8;
    --next-bg: #1d2a44; --next-fg: #9dbcff;
    --int-bg: #2c2340; --int-fg: #c7aefa;
    --offer-bg: #17321f; --offer-fg: #86d9a4;
    --rej-bg: #3a1f1f; --rej-fg: #f0a3a3;
    color-scheme: dark;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--text);
  font: 15px/1.5 "Segoe UI", system-ui, -apple-system, sans-serif;
}
main { max-width: 960px; margin: 0 auto; padding: 32px 16px 64px; }
header { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 8px; }
h1 { font-size: 26px; margin: 0; letter-spacing: -0.01em; }
h2 { font-size: 16px; margin: 36px 0 12px; }
.muted { color: var(--muted); }
.small { font-size: 13px; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-top: 20px; }
.stat { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px; }
.stat b { display: block; font-size: 28px; line-height: 1.1; font-variant-numeric: tabular-nums; }
.stat span { font-size: 13px; color: var(--muted); }

.badge {
  display: inline-block; padding: 2px 10px; border-radius: 999px;
  font-size: 12.5px; font-weight: 600; white-space: nowrap;
}
.s-mottatt, .s-annet { background: var(--wait-bg); color: var(--wait-fg); }
.s-neste_steg { background: var(--next-bg); color: var(--next-fg); }
.s-intervju { background: var(--int-bg); color: var(--int-fg); }
.s-tilbud { background: var(--offer-bg); color: var(--offer-fg); }
.s-avslag { background: var(--rej-bg); color: var(--rej-fg); }

.feed { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
.feed-item { display: grid; grid-template-columns: auto 1fr auto; gap: 4px 12px; align-items: center; padding: 12px 16px; border-top: 1px solid var(--border); }
.feed-item:first-child { border-top: 0; }
.feed-item .title { font-weight: 600; }
.feed-item .subject { grid-column: 2 / 4; font-size: 13px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.empty { padding: 20px 16px; color: var(--muted); }

.toolbar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 12px; }
.chip {
  border: 1px solid var(--border); background: var(--surface); color: var(--text);
  border-radius: 999px; padding: 5px 12px; font: inherit; font-size: 13px; cursor: pointer;
}
.chip[aria-pressed="true"] { background: var(--text); color: var(--bg); border-color: var(--text); }
.chip .n { opacity: .65; margin-left: 4px; }
input[type=search] {
  flex: 1 1 180px; min-width: 0; border: 1px solid var(--border); background: var(--surface); color: var(--text);
  border-radius: 8px; padding: 6px 10px; font: inherit; font-size: 14px;
}

.apps { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
details { border-top: 1px solid var(--border); }
details:first-child { border-top: 0; }
summary {
  list-style: none; cursor: pointer; padding: 12px 16px;
  display: grid; grid-template-columns: minmax(0, 1fr) auto 110px 16px; gap: 12px; align-items: center;
}
summary::-webkit-details-marker { display: none; }
summary:hover { background: var(--hover); }
summary .company { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
summary .company small { display: block; font-weight: 400; font-size: 13px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; }
summary .when { font-size: 13px; color: var(--muted); text-align: right; }
summary .chev { color: var(--muted); transition: transform .15s; }
details[open] summary .chev { transform: rotate(90deg); }
.timeline { list-style: none; margin: 0; padding: 4px 16px 16px 16px; }
.timeline li { display: grid; grid-template-columns: 70px auto 1fr; gap: 10px; align-items: baseline; padding: 6px 0; font-size: 13.5px; }
.timeline .date { color: var(--muted); font-variant-numeric: tabular-nums; }
.timeline .subj { min-width: 0; overflow-wrap: anywhere; }

@media (max-width: 600px) {
  summary { grid-template-columns: minmax(0, 1fr) auto 16px; }
  summary .when { display: none; }
  .timeline li { grid-template-columns: 56px 1fr; }
  .timeline li .badge { grid-column: 2; justify-self: start; }
  .timeline li .subj { grid-column: 2; }
}
</style>
</head>
<body>
<main>
  <header>
    <h1>Jobbsøknader</h1>
    <span class="muted small" id="updated"></span>
  </header>
  <section class="stats" id="stats"></section>

  <h2>Siste svar</h2>
  <div class="feed" id="feed"></div>

  <h2>Alle søknader</h2>
  <div class="toolbar" id="toolbar">
    <input type="search" id="q" placeholder="Søk etter bedrift eller stilling" aria-label="Søk">
  </div>
  <div class="apps" id="apps"></div>
  <p class="muted small">Feil bedrift eller status? Be Claude rette det, for eksempel «skjul Epinova fra søknadsoversikten».</p>
</main>
<script>
const DATA = __DATA__;
const STATUS = {
  mottatt: "Venter på svar", neste_steg: "Neste steg", intervju: "Intervju",
  tilbud: "Tilbud", avslag: "Avslag", annet: "Annet",
};
const EVENT = { ...STATUS, mottatt: "Søknad mottatt" };
const FILTERS = [
  ["alle", "Alle"], ["mottatt", "Venter"], ["prosess", "I prosess"],
  ["tilbud", "Tilbud"], ["avslag", "Avslag"],
];
const apps = DATA.applications;
const now = Date.now() / 1000;

function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") el.className = v; else el.setAttribute(k, v);
  }
  for (const c of children.flat()) if (c != null) el.append(c);
  return el;
}
const badge = (cat, label) => h("span", { class: "badge s-" + cat }, label);
const date = ts => new Date(ts * 1000).toLocaleDateString("nb-NO", { day: "numeric", month: "short" });
function ago(ts) {
  const d = Math.floor((now - ts) / 86400);
  if (d <= 0) return "i dag";
  if (d === 1) return "i går";
  if (d < 14) return `for ${d} dager siden`;
  return date(ts);
}
const inProcess = a => a.status === "neste_steg" || a.status === "intervju";
const matches = (a, f) => f === "alle" || (f === "prosess" ? inProcess(a) : a.status === f);

// Oversikt
document.getElementById("updated").textContent =
  "Sist sjekket " + (DATA.last_check_ts ? ago(DATA.last_check_ts) + " kl. " +
  new Date(DATA.last_check_ts * 1000).toLocaleTimeString("nb-NO", { hour: "2-digit", minute: "2-digit" }) : "aldri");
const answered = apps.filter(a => a.status !== "mottatt").length;
const stats = [
  [apps.length, "søknader"],
  [apps.filter(a => a.status === "mottatt").length, "venter på svar"],
  [apps.filter(inProcess).length, "i prosess"],
  [apps.filter(a => a.status === "tilbud").length, "tilbud"],
  [apps.filter(a => a.status === "avslag").length, "avslag"],
  [apps.length ? Math.round(100 * answered / apps.length) + " %" : "–", "har svart"],
];
document.getElementById("stats").append(...stats.map(([n, l]) => h("div", { class: "stat" }, h("b", {}, String(n)), h("span", {}, l))));

// Siste svar: alt som ikke bare er en kvittering
const feed = document.getElementById("feed");
const answers = apps.flatMap(a => a.events.filter(e => e.category !== "mottatt").map(e => ({ ...e, company: a.company })))
  .sort((x, y) => y.received_ts - x.received_ts).slice(0, 10);
if (!answers.length) feed.append(h("div", { class: "empty" }, "Ingen svar ennå. Du får et varsel så snart en bedrift svarer."));
for (const e of answers) {
  feed.append(h("div", { class: "feed-item" },
    badge(e.category, EVENT[e.category] || e.category),
    h("span", { class: "title" }, e.company),
    h("span", { class: "muted small" }, ago(e.received_ts)),
    h("a", { class: "subject", href: e.url, target: "_blank", rel: "noopener" }, e.subject || "(uten emne)"),
  ));
}

// Alle søknader, med filter og søk som huskes i adressen
const toolbar = document.getElementById("toolbar");
const q = document.getElementById("q");
const params = new URLSearchParams(location.hash.slice(1));
let filter = params.get("f") || "alle";
q.value = params.get("q") || "";
const chips = FILTERS.map(([key, label]) => {
  const n = apps.filter(a => matches(a, key)).length;
  const b = h("button", { class: "chip", type: "button" }, label, h("span", { class: "n" }, String(n)));
  b.onclick = () => { filter = key; render(); };
  b.dataset.key = key;
  return b;
});
toolbar.prepend(...chips);
q.oninput = render;

function render() {
  chips.forEach(c => c.setAttribute("aria-pressed", String(c.dataset.key === filter)));
  history.replaceState(null, "", "#" + new URLSearchParams({ f: filter, q: q.value }));
  const term = q.value.trim().toLowerCase();
  const list = apps.filter(a => matches(a, filter) &&
    (!term || [a.company, ...a.roles, ...a.events.map(e => e.subject)].join(" ").toLowerCase().includes(term)));
  const root = document.getElementById("apps");
  root.replaceChildren();
  if (!list.length) { root.append(h("div", { class: "empty" }, "Ingen søknader her.")); return; }
  for (const a of list) {
    const sub = a.roles.length ? a.roles.join(", ") : "Søkt " + date(a.applied_ts);
    const waited = Math.max(0, Math.floor((now - a.applied_ts) / 86400));
    const when = a.status !== "mottatt" ? ago(a.updated_ts)
      : waited === 0 ? "søkt i dag" : waited === 1 ? "venter 1 dag" : `venter ${waited} dager`;
    root.append(h("details", {},
      h("summary", {},
        h("span", { class: "company" }, a.company, h("small", {}, sub)),
        badge(a.status, STATUS[a.status] || a.status),
        h("span", { class: "when" }, when),
        h("span", { class: "chev", "aria-hidden": "true" }, "›"),
      ),
      h("ul", { class: "timeline" }, [...a.events].reverse().map(e => h("li", {},
        h("span", { class: "date" }, date(e.received_ts)),
        badge(e.category, EVENT[e.category] || e.category),
        h("a", { class: "subj", href: e.url, target: "_blank", rel: "noopener" }, e.subject || "(uten emne)"),
      ))),
    ));
  }
}
render();

// Siden skrives på nytt hvert 15. minutt; last inn på nytt når du kommer tilbake til fanen.
const loaded = Date.now();
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && Date.now() - loaded > 5 * 60 * 1000) location.reload();
});
</script>
</body>
</html>
"""
