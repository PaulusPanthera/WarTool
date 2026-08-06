WARtool v0.8.14 repair patch

Apply this patch over the current WARtool v0.8.13 repository.
Copy everything inside the ZIP into the connected WarTool repository folder and replace matching files.

Changes:
- separate Old Rod, Good Rod and Super Rod throughout the ranking data and UI
- build Rod + Lure as 95% selected rod table + 5% Water Lure-exclusive slot
- keep Safari rods separate and keep Chum variants tied to the selected rod
- repair the v0.8.13 validator/version failure
- show total points and no-species-bonus points as separate leaderboard columns
- exclude only the team-first species/evolution-line bonus from that secondary score
- add rod, Lure provenance and leaderboard scoring regression checks

Suggested commit:
Fix rod methods and leaderboard update v0.8.14
