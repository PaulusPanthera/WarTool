# WARtool v0.8.13

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



## Player leaderboards

The Players tab displays one leaderboard for each competition team. Every active
roster member is included and ranked by scored points, then catch count, unique
evolution lines and name. Each player and team total also shows **no-bonus
points**, which exclude the first evolution-line, Secret Shiny and Safari
bonuses while retaining the normal Alpha, Egg and duplicate base-point rules.

## Automatic week and game time

Week and Time use automatic filters by default:

- assumed event weeks are UTC blocks for Aug 1–7, 8–14, 15–21 and 22–28;
- PokeMMO game time runs four times real time and is derived from UTC;
- Morning is 04:00–10:59 GT, Day is 11:00–20:59 GT and Night is 21:00–03:59 GT;
- the context label refreshes every 15 seconds and the rankings refresh when the
  active period changes;
- manual Week or Time selections remain available.

## Encounter source

The ranking data was rebuilt from `dump(10).zip`, exported on 2026-08-06. The
rebuild keeps the new location and Lure tables while removing encounter rows
that disappeared from the client dump.

## Safari rotational estimates

The undocumented Safari slots remain explicit instead of being redistributed:

- Johto Safari grass: 10% rotational/block slot
- Great Marsh grass: 20% daily-rotation slot
- With Lure: 9.5% and 19% respectively, plus the separate 5% Lure slot

Both rotational slots are unscored by default. Set a Tier 0–7 estimate in the
Settings tab. A published Settings sheet can provide the team default, while
each visitor may keep a local browser override for the rotation they currently
see.

## Safari capture estimates

The default Safari model weights each species by a bundled community
balls-only capture estimate where Johto Safari or Great Marsh data can be
matched. Unknown rotationals, unmatched species, Kanto Safari and Hoenn Safari
use the editable 52% success fallback. Settings may instead select a single
global catch-success override for every Safari species.

## Shiny-safety model

Safety warnings are generated from `data/safety-rules.json`. The rules distinguish
self-KO, self-damage, escape, redirection, held-item, PP/Struggle and
setup-dependent risks. Move warnings only appear when the move can occupy one
of the wild Pokémon's reconstructed four level-up move slots at that location's
level range. Unverified mechanics are labeled as such instead of being shown as
confirmed dangers, and Safari encounters suppress battle hazards entirely.

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
