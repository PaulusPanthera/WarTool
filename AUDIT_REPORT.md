# WARtool v0.8.0 live-pipeline audit

## Scope

This patch connects the three published Google Sheet CSV tabs to the existing
GitHub Pages deployment without adding a browser-side Google request or a
permanent backend.

Configured sources:

- MÜSH To My Surprise — gid `1080256717`
- MÜSH More Like It — gid `1113023649`
- Settings — gid `1365503836`

## Architecture

```text
Google Sheet CSV tabs
        ↓
tools/import_google_sheet.py
        ↓
data/live/state.json + import-report.json
        ↓
static validation and GitHub Pages deployment
```

The importer runs on pushes, manual workflow runs, and every five minutes. It
does not commit generated catch data to Git history.

## Import validation

- team tabs are forced into their corresponding packaged team
- players are validated against the correct 30-player roster
- Pokémon are validated against all 601 scored species
- German `DD.MM.YYYY` dates and optional times are supported
- blank dates retain deterministic Sheet-row ordering
- `TRUE/FALSE`, blank, `yes/no`, `x`, and German boolean variants are handled
- unknown player/Pokémon rows are rejected and listed in the report
- blank/decorative Sheet rows are ignored
- malformed sources or missing headers stop the new deployment
- output files are replaced atomically only after a successful import

## Automated checks completed

- offline importer fixture: 4 valid catches accepted
- wrong-team/unknown player fixture: 1 row rejected and reported
- Settings fixture: 23 values accepted
- generated live-state fixture: 4 catches scoring 80 points
- clean repository state: 0 bundled catches
- JavaScript syntax: passed
- Python compilation: passed
- static WARtool validation: passed
- Pokémon: 601
- evolution lines: 282
- ranking groups: 15,569
- encounter methods: 16
- sprite files: 1,202
- roster: 30 + 30 players, separated
- GitHub Pages artifact: 1,219 files
- local health endpoint: WARtool 0.8.0 on port 8877
- local HTTP page smoke: passed

## Network limitation of this build environment

The sandbox used to build this patch could not resolve external Google hosts,
so the exact three live CSV responses could not be downloaded here. The
importer was tested with CSV fixtures matching the published Sheet structure.
The first GitHub Actions run after pushing this patch is the real network and
permission verification; a failure will leave the existing v0.7.1 deployment
online.
