# WARtool v0.7.1

Static PokeMMO Shiny Wars hunt planner and team-progress website. This is the GitHub publication release candidate before the Google Sheet importer is connected.

## Local launch

Double-click `START_HERE.bat` and keep the command window open. WARtool uses `http://localhost:8877` to avoid collisions with PaxDex. The local server disables browser caching during development.

## Release state

- no caught shinies are bundled
- both 30-player MÜSH competition teams remain separate
- the Caught Shinies page is ready for generated live data
- the website reads `data/live/state.json` from its own origin
- GitHub Pages deployment is included
- the Google Sheet importer is the next pipeline patch

## Encounter data

- ordinary 5% horde blocks are normalized conditionally
- exact 100% early-route Sweet Scent-only tables are valid
- 99.99% near-complete Sweet Scent tables remain warnings
- Lostlorn Forest Zorua uses a temporary 5% conditional 3× horde share
- Safari Zone Gate remains a normal Headbutt location

Rebuild and validate with:

```text
python tools/rebuild_encounters.py path\to\dump.zip
python tools/validate_static.py
```

Follow `GITHUB_SETUP.md` to publish.
