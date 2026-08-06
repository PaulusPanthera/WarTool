# WARtool v0.8.13 — dump(10) and no-bonus leaderboard points

## Encounter-data update

- Rebuilt all hunt groups from `dump(10).zip` exported on 2026-08-06.
- Updated the generated dump SHA-256 and source metadata.
- Accepted the new client location/Lure tables.
- Removed obsolete encounter rows no longer present in the dump.
- Updated all data-regression expectations without changing scoring rules.

## Player leaderboards

- Player rows now show total scored points and points without bonuses.
- Team headers now show total scored points and team points without bonuses.
- “No bonus” excludes:
  - first evolution-line bonus;
  - Secret Shiny bonus;
  - Safari catch bonus.
- Alpha, Egg and duplicate values remain part of the base score.
- Leaderboard ordering remains based on the official total score.

## Validation

- 601 scored Pokémon across 282 evolution lines.
- 16,119 display groups across 14 ranked methods.
- 1,202 normal/shiny sprites verified.
- Safari and shiny-safety invariants passed.
- Google Sheet and GitHub Pages contracts passed.
