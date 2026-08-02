WARtool v0.8.10 full-slowdown alternative patch

This patch supersedes v0.8.9.
Copy everything inside this ZIP into the connected WarTool repository folder
and replace matching files.

Suggested commit:
Show full slowdown alternative v0.8.10

Behavior:
- One ranking card per hunt.
- Horde cards with any start-delay ability show a standard score and a 100%
  slowed alternative score.
- The warned Pokémon's encounter share does not interpolate the alternative.
- Horde cards without a start-delay warning show only one score.
- Safari remains excluded from start-delay handling.
