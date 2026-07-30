# WARtool v0.7.1 release audit

**Status: PASS — ready for GitHub Pages publication.**

## Dark-mode readability hotfix

- Fixed the unreadable Pokémon composition chips inside the light-green best-hunt card.
- Best-hunt chips now deliberately stay cream with dark text in dark mode.
- Alternative-card chips use bright text on a dark green surface.
- Increased contrast for labels, metadata, secondary text, form hints, source status, cards and dialogs.
- Missing evolution lines remain visually secondary, but their dark-mode opacity increased from 28% to 58%; hover restores full opacity.
- Dark-mode top bar and primary buttons were darkened to retain clear white text.

Measured representative contrast ratios:

- Best-hunt chip: **12.59:1**
- Alternative hunt chip: **11.96:1**
- Secondary text on dark cards: **8.79:1**
- Console labels: **7.54:1**
- Console values: **9.00:1**
- Header text: **5.49:1**

## Functional and browser smoke test

- Rankings, Caught Shinies, Tier Progress, Settings and Data pages all rendered and switched correctly.
- Best result and alternative hunt cards rendered in dark mode.
- Desktop browser errors: **0**.
- Visible fatal errors: **0**.
- Mobile layout rendered without horizontal document overflow.
- Packaged team state remains empty: **0 catches / 0 points**.
- No service worker or opaque cache layer is registered.

## Encounter and scoring audit

- **601** scored Pokémon
- **282** evolution lines
- **15,569** ranking groups across **16** methods
- **1,202** normal/shiny sprites verified
- **60** players in two separate 30-player teams
- **163** incomplete groups hidden by default
- **0** fatal validation errors
- Exact **100%** early-route Sweet Scent-only tables remain accepted.
- Near-100% **99.99%** tables remain warnings.
- Lostlorn Forest Zorua remains a disclosed temporary **5% conditional 3× horde** assumption.

## Code and deployment checks

- `node --check js/app.js`: PASS
- Python compilation: PASS
- `python tools/validate_static.py`: PASS
- GitHub Pages build: **1,217 files**
- Local health endpoint: WARtool **0.7.1**, port **8877**
- Local server sends no-cache headers

## Remaining work

The Google Sheet importer is not connected yet. The next patch should download the published team tabs in GitHub Actions, validate them, and generate `data/live/state.json` before deployment.
