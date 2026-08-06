# WARtool v0.8.14 — rod methods and leaderboard repair

## Repaired v0.8.13 update

- Fixed the release validator mismatch that caused the uploaded v0.8.13 project to fail with `application logic is missing: no bonus`.
- Kept the intended secondary leaderboard score but made it a separate visible column.
- The secondary value now removes **only** the team-first species/evolution-line bonus.
- Secret Shiny and Safari bonuses still count, together with the normal Alpha, Egg and duplicate rules.

## Fishing methods

- Old Rod, Good Rod and Super Rod are now separate methods on ranking cards, filters, dialogs and CSV exports.
- Safari Old Rod, Safari Good Rod and Safari Super Rod are also separate.
- Rod + Lure is generated as:
  - 95% of the selected rod table;
  - 5% of the exact Water Lure-exclusive slot for that location, season and time.
- A lure-exclusive Pokémon already present in the selected rod table keeps both contributions instead of one overwriting the other.
- Chum Bucket variants keep the selected rod composition.
- Existing generic fishing-speed settings remain compatible; no Sheet migration is required.

## Additional repairs

- Fixed generated metadata totals so complete and incomplete raw variants add up to the reported total.
- Equivalent submaps with the same visible region/location name no longer appear twice in the card/dialog display.
- Added regression checks for rod identity, Lure provenance, Safari rod separation, speed aliases and no-species-bonus scoring.

## Generated totals

- 601 scored Pokémon across 282 evolution lines.
- 17,680 display groups across 28 visible methods.
- 5,650 rod-specific groups.
- 3,799 Rod + Lure groups.
- 700 Safari groups, including 234 Safari rod groups.
- 59,814 raw variants: 59,790 complete and 24 incomplete.
