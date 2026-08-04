# WARtool v0.8.12 — Update audit

## Added

- New Players navigation tab.
- Separate player leaderboard for each of the two competition teams.
- All active roster members appear, including zero-point players.
- Sorting: points, catches, unique evolution lines, then player name.
- Team points and catch totals shown on each board.
- Automatic Week and Time options are now the defaults.
- Live PokeMMO game-time label and assumed current event week.
- Automatic context refresh every 15 seconds and on tab visibility return.
- Reset Filters restores both automatic selections.

## Time model

The user calibration was 11:36 CEST / 09:36 UTC corresponding to approximately
14:26 game time. Four-times UTC produces 14:24 at exactly 09:36:00 and 14:26 at
09:36:30, matching the supplied observation without an arbitrary offset.

Implemented game periods:

- Morning: 04:00–10:59 GT
- Day: 11:00–20:59 GT
- Night: 21:00–03:59 GT

Temporary event-week assumption:

- Week 1: Aug 1–7 UTC
- Week 2: Aug 8–14 UTC
- Week 3: Aug 15–21 UTC
- Week 4: Aug 22–28 UTC
- outside the window: all weeks

## Verification

- Python compilation passed.
- JavaScript syntax passed.
- Static validator passed.
- GitHub Pages artifact built with 1,222 files.
- Fixed-time clock calibration passed: 2026-08-04 09:36:30 UTC → 14:26 Day.
- Morning, Day and Night boundary tests passed.
- All four assumed week-boundary tests passed.
- Two-team leaderboard scoring, sorting, catch counts and unique-line counts passed.
- Cross-team catch leakage test passed.
- Existing 601 Pokémon, 282 evolution lines and 14,985 ranking groups remained unchanged.

Chromium DOM smoke execution was attempted, but the installed container Chromium
process did not finish in headless mode. Static structure, runtime logic and data
contracts were instead covered by the validator and isolated Node execution.
