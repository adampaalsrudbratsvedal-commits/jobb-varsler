# Jobbvarsler

Går gjennom Gmail og varsler deg når du får jobbrelatert tilbakemelding: mottatt søknad,
intervju, avslag, tilbud eller neste steg.

To deler deler samme logikk og tilstand (`data/state.json`), så du aldri får samme varsel to ganger:

- **Bakgrunnsjobb** (`poll.py`): Windows Oppgaveplanlegger kjører den hvert 15. minutt og viser
  et Windows-varsel. Klikker du på varselet, åpnes e-posten i Gmail.
- **MCP-server** (`server.py`): gir Claude verktøyene `check_job_feedback`, `list_job_feedback`
  `scan_job_feedback` og `read_email`, så du kan spørre «har jeg fått svar på noen søknader denne uka?».

Slik vurderes hver e-post: et nøkkelordfilter (`KEYWORDS` i `jobbvarsler/config.py`) luker ut
det meste. Treffene sorteres så med gratis fraseregler (`jobbvarsler/rules.py`), som skiller ut
stillingsvarsler, engangskoder og lignende og setter en kategori. Det koster ingenting.

Setter du en Claude API-nøkkel, tar Claude over sorteringen og lager en kort oppsummering. Det er
valgfritt og koster litt per e-post. Bruker du MCP-serveren i Claude-chatten, er det uansett
Claude som tolker funnene, og kan lese hele e-posten med `read_email`.

## Oppsett

### 1. Gi programmet lov til å lese Gmail (ca. 10 min, bare én gang)

Google krever at alle programmer som leser Gmail, har sin egen tilgangsfil. Den lager du gratis til deg selv.
Menyene kan hete litt forskjellig (norsk/engelsk), men rekkefølgen er den samme.

1. Gå til <https://console.cloud.google.com/> og logg inn med Gmail-kontoen din.
2. **Lag et prosjekt:** klikk på prosjektvelgeren øverst til venstre, så **Nytt prosjekt**. Kall det
   `Jobbvarsler` og klikk **Opprett**. Sjekk at det nye prosjektet er valgt øverst.
3. **Skru på Gmail API:** skriv `Gmail API` i søkefeltet øverst, klikk på treffet og så **Aktiver**.
4. **Lag innloggingsskjermen:** gå til *APIer og tjenester → OAuth-samtykkeskjerm* (kan også hete
   *Google Auth Platform*) og klikk **Kom i gang**.
   - Appnavn: `Jobbvarsler`, e-post: din egen
   - Målgruppe: **Ekstern**
   - Kontaktinformasjon: din egen e-post
   - Godta vilkårene og klikk **Opprett**
5. **Legg deg selv til som testbruker:** gå til **Målgruppe**, så **Testbrukere → Legg til brukere**,
   skriv inn Gmail-adressen din og klikk **Lagre**.
6. **Lag tilgangsfilen:** gå til **Klienter → Opprett klient**, velg programtypen **Skrivebordsapp**,
   klikk **Opprett** og så **Last ned JSON**.
7. **Flytt filen:** den havner i Nedlastinger med et langt navn (`client_secret_....json`). Gi den
   det nye navnet `credentials.json` og legg den i `C:\Users\adamp\jobb-varsler\data\`.

**Valgfritt, men lurt:** klikk **Publiser app** under *Målgruppe*. Ellers må du logge inn på nytt hver 7. dag.

### 2. Logg inn (1 min)

```bash
C:\Users\adamp\jobb-varsler\.venv\Scripts\python.exe C:\Users\adamp\jobb-varsler\login.py
```

Nettleseren åpnes, og du velger Gmail-kontoen din.

- Ser du «Google har ikke bekreftet denne appen», er det normalt, fordi du har laget appen selv.
  Klikk **Fortsett**.
- Gi tilgang til å *lese* e-post og klikk **Fortsett**.

Terminalen skriver da «Innlogget som …». Programmet kan bare lese e-post, ikke sende, slette eller endre noe.

### 3. Claude-nøkkel (valgfritt, koster penger)

Programmet spør Claude om hver e-post som kan være jobbrelatert. Det krever en API-nøkkel og litt
kreditt på Anthropic-kontoen. Dette er separat fra et Claude-abonnement.

1. Gå til <https://console.anthropic.com/>, velg **API Keys → Create Key** og kopier nøkkelen.
   Den vises bare én gang.
2. Lagre den på PC-en (lim inn nøkkelen i stedet for `sk-ant-...`):

   ```bash
   setx ANTHROPIC_API_KEY "sk-ant-..."
   ```

3. Lukk terminalen og åpne en ny.

Hopper du over dette steget, brukes de gratis reglene. De traff riktig på alle e-postene i testen.

### 4. Koble MCP-serveren til Claude

Claude Code:

```bash
claude mcp add --scope user jobb-varsler -- "C:\Users\adamp\jobb-varsler\.venv\Scripts\python.exe" "C:\Users\adamp\jobb-varsler\server.py"
```

Claude Desktop legger du inn i `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "jobb-varsler": {
      "command": "C:\\Users\\adamp\\jobb-varsler\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\adamp\\jobb-varsler\\server.py"]
    }
  }
}
```

### 5. Skru på varsler i bakgrunnen

```bash
powershell -ExecutionPolicy Bypass -File scripts\installer-bakgrunnsjobb.ps1
```

Vil du sjekke oftere, bruker du for eksempel `-Minutter 5`. Du fjerner oppgaven med
`scripts\avinstaller-bakgrunnsjobb.ps1`.

## Test manuelt

```bash
.venv\Scripts\python.exe poll.py
```

Første kjøring ser 3 dager tilbake. Logg: `data/jobbvarsler.log`.

## Tilpasning

- `jobbvarsler/config.py`: nøkkelord, modell, hvor langt tilbake første kjøring ser.
- `jobbvarsler/classifier.py`: hva Claude regner som tilbakemelding, og kategoriene.
- `jobbvarsler/notify.py`: varseltekstene.

Vil du bare varsles om intervju og tilbud, filtrerer du på `category` i `notify_findings`.
