# WARtool v0.8.11 — Safety audit corrections

This patch applies the WARtool findings from the 2026-08-02 WARtool/PaxDex
functionality and shiny-safety audit.

## Corrected defects

- Curse now warns only for Ghost-type users.
- Removed 130 false non-Ghost Curse warning rows across 122 previous groups.
- Head Smash advice now recommends Rock resistance and high Defense instead of
  incorrectly suggesting Ghost immunity.
- Memento advice now states explicitly that trapping alone does not prevent it.
- Rage Powder and Follow Me now have separate, move-specific counter guidance.
- Hoppip/Skiploom Rage Powder guidance includes the Worry Seed/Overcoat caveat.

## Added safety categories

- Escape risk: Teleport.
- Held-item risk: Sticky Barb.
- PP/Struggle preparation: Smeargle + Sketch and Ditto + Transform/Imposter.
- Setup-dependent interaction: Trick and Switcheroo.
- Compound Hoppip/Skiploom preparation guidance.

## Verification handling

- Healing Wish is no longer shown as a confirmed critical danger; it is marked
  as preparation-level and needs in-game verification.
- Dry Skin and Solar Power are marked as weather-dependent and unverified
  because the encounter dump does not expose active battle weather.
- Unverified Roar/Whirlwind, Dragon Tail/Circle Throw and Drifblim Destiny Bond
  interactions were intentionally not added.
- Koffing/Weezing Reactive Gas + Damp wording no longer makes a categorical
  claim; Imprison is presented as the conservative option pending verification.

## Shared rules

`data/safety-rules.json` is now the structured source for move, ability,
held-item, species and compound warnings. Generated rows include category,
severity, context and verification status.
