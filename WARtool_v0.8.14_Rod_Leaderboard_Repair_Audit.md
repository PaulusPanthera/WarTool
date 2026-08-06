# WARtool v0.8.14 — rod and leaderboard repair audit

**Audit date:** 2026-08-06  
**Input project:** uploaded v0.8.13 repository snapshot  
**Encounter source:** `dump(10).zip`

## Executive result

The corrected v0.8.14 project passes the static validator, deterministic encounter rebuild, Python/JavaScript syntax checks, offline Sheet import, local-server health checks and GitHub Pages build.

The uploaded v0.8.13 project did not pass its own validator. The failure was caused by an obsolete literal check for `no bonus` after the UI had already been renamed to `no species bonus`. The leaderboard calculation was mostly repaired by the fast fix, but its secondary value was visually buried and the release remained invalid.

The fishing implementation also had two functional defects:

1. Old Rod, Good Rod and Super Rod were collapsed into one generic `Fishing` method, allowing distinct rod tables to merge.
2. `Fishing + Lure` cloned the surfing/Lure table instead of preserving the selected rod table.

Both defects are fixed.

## Implemented behavior

### Rod identity

Every fishing hunt now identifies its required rod:

- Old Rod
- Good Rod
- Super Rod
- each non-Safari Chum variant
- each Rod + Lure variant
- each Rod + Lure + Chum variant
- Safari Old/Good/Super Rod and their Lure variants

The website still maps these visible methods to the existing generic fishing-speed settings. Existing local settings and the published Settings Sheet therefore continue to work without new rows.

### Rod + Lure composition

For every exact location, season and time where the dump exposes a Water Lure-exclusive slot:

- selected rod table contribution = 95%;
- Water Lure-exclusive slot contribution = 5%.

The generator preserves `baseShare` and `lureShare` per component. If the Lure-slot species is already available from the rod, the two contributions are added rather than overwritten. The dialog identifies base, Lure and combined contributions.

### Leaderboards

Each player board and team header now shows two separate values:

- official total points;
- points with only the team-first species/evolution-line bonus removed.

The secondary score still includes Secret Shiny and Safari bonuses. It also retains Alpha, Egg and duplicate scoring rules. Ranking order remains based on total points.

### Other repaired issues

- v0.8.13 validator/release mismatch fixed.
- Raw generated metadata corrected from an inconsistent partial count to:
  - 59,814 total raw variants;
  - 59,790 complete;
  - 24 incomplete.
- Duplicate visible location names caused by separate internal map IDs are collapsed for cards, dialogs and CSV display while the generated data retains the underlying locations.
- Overlapping base/Lure species in ordinary Lure tables retain both contributions.

## Generated-data audit

| Check | Result |
|---|---:|
| Scored Pokémon | 601 |
| Evolution lines | 282 |
| Display groups | 17,680 |
| Visible methods | 28 |
| Raw variants | 59,814 |
| Location/time groups | 27,594 |
| Rod-specific groups | 5,650 |
| Rod + Lure groups | 3,799 |
| Safari rod groups | 234 |
| Safari groups total | 700 |
| Incomplete display groups | 4 |
| Normal/shiny sprites | 1,202 |

Rod integrity checks found:

- zero generic `Fishing` display groups;
- zero rod/method encounter-type mismatches;
- zero Safari Chum variants;
- every Rod + Lure group totals 95% base plus 5% Lure contribution;
- every component's base plus Lure provenance equals its final share.

## Leaderboard regression fixture

A four-catch fixture covering team-first species bonus, Secret, Safari, Egg and duplicate Alpha scoring produced:

- total score: 236;
- score without species bonus: 220;
- player one: 123 total / 115 without species bonus;
- player two: 113 total / 105 without species bonus.

This verifies that the secondary score removes 16 points of species bonus and nothing else.

## Automated checks completed

- Baseline v0.8.13 validator reproduced the failure: **failed as expected**.
- v0.8.14 static validator: **passed**.
- Python compilation: **passed**.
- JavaScript syntax: **passed**.
- JavaScript leaderboard/scoring regression: **passed**.
- Rod speed-alias regression: **passed**.
- PokeMMO automatic-time calibration and quarter-hour transitions: **passed**.
- Duplicate display-location collapse: **passed**.
- Offline Google Sheet importer with current Settings template: **passed**.
- Local server `/__wartool_health`, root page and metadata requests: **passed** with no-cache headers.
- Deterministic rebuild from `dump(10).zip`: **passed**; generated hashes matched exactly.
- GitHub Pages build: **passed**, 1,222 files.

## Deterministic hashes

- `dump(10).zip`: `162992ee87eb99f4163572126c316b41379f0d574c6585c1de70161bc934c1b3`
- `data/groups.js`: `d9745e5a8ec067643a23046c962ca870f8a68f3dd0d6321fa2e331c18391cc9d`
- `data/meta.js`: `c6a374f8e349ed517dbaecb7ce89b45cca819bcbcb7fe41e51fb6e27eea58d52`

## Browser limitation

A true Chromium navigation smoke test cannot be claimed in this environment because localhost/file navigation is blocked by the container's browser policy. The project was instead checked through source-level JavaScript regressions, the local HTTP server, static asset validation and the complete Pages build.
