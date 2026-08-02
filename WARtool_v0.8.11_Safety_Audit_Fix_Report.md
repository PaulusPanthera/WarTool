# WARtool v0.8.11 — Safety audit fix report

## Scope

This is a WARtool patch. It addresses every confirmed WARtool defect from the
2026-08-02 WARtool/PaxDex audit and adds the audit's confirmed shared missing
safety categories. It does not modify PaxDex because the audited PaxDex v0.23
source tree was not part of the WARtool repository patch base.

Mechanics explicitly marked by the audit as requiring manual in-game
verification were not promoted to confirmed dangers.

## Correctness changes

### Curse

- Ghost-type condition added to the shared rule.
- Previous false rows removed: 130.
- Previous affected groups: 122.
- Remaining generated Curse species: Cofagrigus, Dusclops, Gastly, Shuppet and
  Spiritomb.
- Non-Ghost Curse rows after rebuild: 0.

### Advice corrections

- Head Smash: every generated row recommends a Rock-resistant, high-Defense
  target and states that Ghost typing does not block the Rock-type move.
- Memento: every generated row names move denial and states that trapping alone
  does not prevent Memento.
- Rage Powder: faster Extreme Speed/Feint, Taunt/Imprison, Grass and Overcoat
  handling are stated explicitly.
- Follow Me: faster Extreme Speed/Feint and Taunt/Imprison are stated; the text
  explicitly says Grass and Overcoat do not ignore Follow Me.
- Hoppip/Skiploom Rage Powder text includes the Worry Seed caveat.

## New generated warning coverage

| Warning | Ranking groups |
|---|---:|
| Teleport escape risk | 397 |
| Sticky Barb held-item risk | 61 |
| Smeargle + Sketch PP/Struggle | 45 |
| Ditto Transform/Imposter preparation | 272 |
| Trick setup interaction | 122 |
| Switcheroo setup interaction | 16 |
| Hoppip/Skiploom compound setup | 109 |

Species checks:

- Teleport: Abra, Natu and Ralts only.
- Sticky Barb: Cacnea, Cacturne, Ferroseed and Ferrothorn only.
- Safari battle-hazard groups: 0.
- Explicit horde Perish Song warnings: 0.

## Verification-status changes

The generated model now has three statuses:

- `confirmed`
- `community-documented`
- `needs-in-game-test`

Healing Wish, Dry Skin and Solar Power are preparation-level warnings with
`needs-in-game-test`. They are no longer presented as unconditional confirmed
critical hazards.

The following audit items remain excluded pending manual verification:

- Roar and Whirlwind
- Dragon Tail and Circle Throw
- Drifblim Destiny Bond compound behavior

Reactive Gas + Damp is not asserted as settled; the warning recommends
Imprison as the conservative alternative.

## Shared safety model

Added `data/safety-rules.json` with:

- category
- severity
- applicable contexts
- optional species/type conditions
- level-active move behavior
- effect
- recommended preparation
- verification status

WARtool's encounter rebuilder reads this file and emits structured hazard rows.
The browser displays distinct card badges for self-KO, escape, redirection,
self-damage, held-item, PP/Struggle, setup-dependent and unverified risks.

## Rebuild results

- 720 dump monsters loaded.
- 601 scored Pokémon across 282 evolution lines.
- 14,985 ranking groups across 14 methods.
- 7,242 groups with at least one safety warning.
- 2,997 groups with at least one critical warning.
- 6,088 groups with at least one warning-severity entry.
- 929 groups with at least one preparation entry.
- 6,271 start-delay groups retained.
- 494 horde cards retain the separate 100% slowed alternative.
- Safari hazard and slowdown exclusions retained.

The group count changed from 14,987 to 14,985 because removing false Curse
metadata allows two otherwise identical alternative-location groups to merge.
Encounter probabilities and scoring were not changed.

## Automated verification

Passed:

- deterministic rebuild from `dump(8).zip`
- exact repeat-build hashes for `data/groups.js` and `data/meta.js`
- Python compilation for all maintenance scripts and local server
- `node --check js/app.js`
- static project validator
- isolated JavaScript badge/marker rendering test
- offline Google Sheet import fixture with one catch per team
- local server health endpoint and no-cache headers
- GitHub Pages artifact build
- 1,222 artifact files, including the shared safety-rules file

A full Chromium navigation smoke remained unavailable because the execution
environment blocks browser navigation to local HTTP addresses. The static
validator, isolated UI-function test, local HTTP checks and complete build were
used instead.
