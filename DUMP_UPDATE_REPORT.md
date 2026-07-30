# PokeMMO dump update · 2026-07-30

## Compared with the previous encounter dump

- Monster count stayed at **720**.
- Location records changed from **33,249** to **33,231**.
- After canonicalizing formatting noise, encounter-location changes were limited to eight species:
  - Pidgeot: Bond Bridge lure entry removed
  - Leafeon: Bond Bridge lure entry added
  - Croagunk: six winter Grass/horde entries removed
  - Palpitoad: four winter Grass/horde entries removed
  - Karrablast: four winter Grass/horde entries removed
  - Shelmet: four winter Grass/horde entries removed
  - Stunfisk: four winter Grass/horde entries removed
  - Zorua: four seasonal unknown-rate Lostlorn Forest 3× horde entries added

Unknown-rate Zorua records are preserved by the dump comparison. WARtool applies the separately disclosed temporary planning assumption below.

## Temporary Zorua planning assumption

Lostlorn Forest Zorua is modeled as **5% of the conditional 3× horde table** for planning purposes. Existing disclosed species are proportionally rescaled to the remaining 95%. This is explicitly marked as an assumption and is not presented as a confirmed game rate.
