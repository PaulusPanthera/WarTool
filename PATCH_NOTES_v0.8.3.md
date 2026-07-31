# WARtool v0.8.3 — Shiny safety warnings

- Adds red **Self-KO risk** and amber **Self-damage** warnings to hunt rankings.
- Marks the affected Pokémon directly inside encounter compositions.
- Adds exact warning details to the hunt dialog, including wild level range, move or ability, affected locations and practical counter notes.
- Derives possible wild moves from the current dump's encounter levels and last-four level-up moves rather than warning every location where a species exists.
- Covers Selfdestruct/Explosion, Memento-style self-KO moves, recoil and crash moves, confusion-lock moves, Ghost Curse, Belly Drum, Perish Song outside hordes, and conditional sun-damage abilities.
- Treats Reactive Gas + Selfdestruct/Explosion as an Imprison-first case because Damp may be suppressed.
- Excludes Perish Song warnings from horde methods and excludes wild-battle warnings from Fossil revival.
- Adds safety columns to ranking CSV exports and safety terms to ranking search.
- Keeps the interface compact: no additional filter or permanent explanatory panel was added.
