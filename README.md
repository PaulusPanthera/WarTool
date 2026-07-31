# WARtool v0.8.4

Static PokeMMO Shiny Wars hunt planner, caught-shiny tier overview and team
progress website for two separate MÜSH competition teams.

## Live architecture

```text
Published Google Sheet tabs
        ↓
GitHub Action importer
        ↓
data/live/state.json
        ↓
Validated GitHub Pages artifact
```

Visitors never fetch Google Sheets directly. The workflow imports both team
catch tabs and the Settings tab before deployment, then publishes same-origin
JSON. It also refreshes the Pages artifact on a five-minute schedule.

## Shiny safety

Ranking cards flag possible self-KO risks in red and lower-severity self-damage
risks in amber. Opening a hunt shows the exact Pokémon, move or ability, wild
level range, affected locations and counter note. Warnings are rebuilt from the
current encounter dump together with the normal hunt data. Safari Singles and
Lure Safari Singles are excluded because those encounters do not use normal
wild-battle move or ability behavior.

## Local launch

Double-click `START_HERE.bat` and keep the command window open. WARtool uses:

```text
http://localhost:8877
```

The committed `state.json` starts empty. To test the current published Sheet
locally, run `UPDATE_LIVE_DATA.bat` first, then launch WARtool.

## Sheet sources

The three public CSV links are stored in:

```text
data/live/sources.json
```

Optional GitHub repository variables can override them without a code change:

```text
TEAM_SURPRISE_CSV_URL
TEAM_MORE_LIKE_IT_CSV_URL
WAR_SETTINGS_CSV_URL
```

## Validation and build

```text
python tools/import_google_sheet.py
python tools/validate_static.py
python tools/build_static_site.py
```

Encounter-data rebuilds remain separate:

```text
python tools/rebuild_encounters.py path\to\dump.zip
```
