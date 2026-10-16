# Handleiding: wefact-mcp installeren (Windows)

Stappen voor Windows met Claude Desktop. macOS/Linux staat onderaan.
Reken op een kwartier — of twee minuten met de kant-en-klare extensie hieronder.

## Snelste route: kant-en-klare extensie (aanbevolen)

Heb je **Python 3.14 op Windows** (check: stap 1 hieronder)? Download dan
`wefact-mcp.mcpb` van de [laatste release](https://github.com/BE-Zizoo/wefact-mcp/releases/latest)
en dubbelklik erop, of installeer via Claude Desktop → **Settings →
Extensions → Advanced settings → Install Extension…**. Claude vraagt bij de
installatie om je WeFact API-sleutel (aanmaken en IP-whitelist: zie stap 4)
en bewaart die zelf veilig. Alle Python-libraries zitten in de bundel —
stappen 2, 3, 5 en 6 vervallen volledig. Test daarna zoals in stap 7.

De rest van deze handleiding is de handmatige route (werkt op elke
Python-versie vanaf 3.10 en op macOS/Linux).

## 1. Python controleren

Open PowerShell (Start → typ `powershell`) en typ:

```powershell
python --version
```

Zie je `Python 3.10` of hoger, ga naar stap 2. Zie je een foutmelding of een
lagere versie: installeer Python via https://www.python.org/downloads/windows/
en vink bij de installatie **"Add python.exe to PATH"** aan. Sluit daarna
PowerShell en open het opnieuw.

## 2. De code ophalen

Download de zip via GitHub (groene knop **Code → Download ZIP**) of clone:

```powershell
git clone https://github.com/BE-Zizoo/wefact-mcp.git
```

Zet de map op een vaste plek, bijvoorbeeld:

```
C:\Users\stefa\wefact-mcp
```

Die map moet blijven staan; Claude Desktop start de server elke keer van daaruit.
In de rest van deze handleiding heet dit pad `C:\Users\stefa\wefact-mcp` —
vervang het door jouw pad als je een andere map koos.

## 3. Installeren

In PowerShell:

```powershell
cd C:\Users\stefa\wefact-mcp
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

Krijg je bij `activate` een melding over "execution policy"? Voer dan eenmalig
dit uit en probeer opnieuw:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Controleer of alles werkt (nog zonder API-key):

```powershell
pytest
```

Verwacht: `33 passed`.

## 4. API-key aanmaken in WeFact

1. Log in op WeFact → **Instellingen** → **API**.
2. Maak een API-sleutel aan (of kopieer de bestaande).
3. **Whitelist je IP-adres** op diezelfde pagina. Zonder whitelist weigert
   WeFact elke aanroep. Je huidige publieke IPv4-adres vind je op
   https://api.ipify.org (WeFact ondersteunt alleen IPv4).
   Let op: bij een dynamisch IP (thuisverbinding) moet je dit af en toe
   bijwerken; een 403-fout van de server betekent bijna altijd "IP niet
   gewhitelist" of "geblokkeerd na te veel aanroepen".

## 5. API-key invullen

Maak in de map `C:\Users\stefa\wefact-mcp` een kopie van `.env.example` met
de naam `.env`:

```powershell
copy .env.example .env
notepad .env
```

Zet je sleutel achter `WEFACT_API_KEY=` (geen aanhalingstekens, geen spaties):

```
WEFACT_API_KEY=abc123jouwsleutel
```

Opslaan en sluiten. Dit bestand staat in `.gitignore` en verlaat je machine
niet. Dit is de enige plek waar de key hoort te staan.

## 6. Koppelen aan Claude Desktop

1. Open Claude Desktop → **Instellingen** (tandwiel) → **Developer** →
   **Edit Config**. Dat opent de map met `claude_desktop_config.json`
   (normaal `C:\Users\stefa\AppData\Roaming\Claude\`).
2. Open dat bestand in Kladblok en zet er dit in. Staat er al een
   `mcpServers`-blok met andere servers? Voeg dan alleen het `"wefact": {...}`-deel
   toe binnen dat blok, gescheiden door een komma.

```json
{
  "mcpServers": {
    "wefact": {
      "command": "C:\\Users\\stefa\\wefact-mcp\\.venv\\Scripts\\python.exe",
      "args": ["-m", "wefact_mcp"],
      "cwd": "C:\\Users\\stefa\\wefact-mcp"
    }
  }
}
```

Let op de dubbele backslashes `\\` in JSON. `cwd` is nodig zodat de server je
`.env` vindt. (Alternatief: laat `.env` weg en zet
`"env": { "WEFACT_API_KEY": "..." }` in dit blok — dan staat de key in de
config van Claude in plaats van in `.env`. Kies één van beide.)

Gebruik je de extensie uit de snelste route? Zet dan géén `wefact`-blok in
deze config — anders draait de server dubbel en zie je elke tool twee keer.

3. Sla op en **sluit Claude Desktop volledig af** (ook via het systeemvak
   rechtsonder → Quit) en start het opnieuw.

## 7. Testen

Typ in Claude Desktop:

> Gebruik de wefact-tool `whoami`.

Je krijgt het aantal debiteuren en de eerste DebtorCode terug. Daarna bijvoorbeeld:

> Lijst de 5 meest recente verzonden facturen.

Bij fouten staat de oorzaak in het antwoord (`message` en `errors`):

| Melding | Oorzaak |
|---|---|
| `WEFACT_API_KEY is not set` | `.env` ontbreekt of staat niet in de `cwd`-map; of de key staat niet achter `WEFACT_API_KEY=` |
| `HTTP 403` / "firewall" | IP niet gewhitelist in WeFact, of tijdelijk geblokkeerd (wacht een uur) |
| `errors: ["... api_key ..."]` | sleutel verkeerd gekopieerd |
| Server verschijnt niet in Claude | pad in de config klopt niet, of Claude was niet volledig afgesloten. Logs: `%APPDATA%\Claude\logs\mcp-server-wefact.log` |

## Andere clients

Claude Code:

```powershell
claude mcp add wefact -e WEFACT_API_KEY=jouw-key -- C:\Users\stefa\wefact-mcp\.venv\Scripts\python.exe -m wefact_mcp
```

Cursor / andere MCP-clients: zelfde `command`, `args` en `cwd` als hierboven.

## macOS / Linux

```bash
cd ~/wefact-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env    # key invullen
pytest
```

Config: `~/Library/Application Support/Claude/claude_desktop_config.json` met
`"command": "/Users/jij/wefact-mcp/.venv/bin/python"` en dezelfde `args`/`cwd`.

## Updaten

Extensie: download de nieuwe `.mcpb` van de laatste release en installeer
hem opnieuw (instellingen zoals je API-sleutel blijven bewaard).

Handmatige installatie: `git pull` in de map (of nieuwe zip over de bestaande
map uitpakken; `.env` blijft staan), dan in PowerShell in die map:
`.venv\Scripts\activate` en `pip install -e ".[dev]"`, Claude Desktop
herstarten.
