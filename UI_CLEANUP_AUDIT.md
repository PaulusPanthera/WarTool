# WARtool v0.8.1 UI cleanup audit

## Changes verified

- Ranking limit options: 24, 50, 100, 250, 500, 1,000, All.
- Default result count: 100.
- All mode: progressive 250-card chunks with no hard result cap.
- Compact six-column desktop filter layout.
- Shortened navigation, headings, labels, notices and footer.
- Local preview and backup controls hidden unless localhost uses `?preview=1`.
- Empty catch board shows one empty state instead of eight repeated messages.
- Repeated encounters/hour helper text removed from Settings.

## Full-package checks

- Static validator: passed.
- Pokémon: 601 species across 282 evolution lines.
- Ranking groups: 15,569 across 16 methods.
- Packaged catches: 0.
- JavaScript syntax: passed.
- Python compilation: passed.
- GitHub Pages build: passed, 1,219 files.

## Browser smoke check

A representative 300-group runtime build was tested in Chromium:

- no JavaScript page errors;
- default 100 selection loaded;
- All mode initially rendered ranks 1–250 and enabled progressive loading;
- dark and light rankings rendered;
- empty Catches page remained compact;
- local-only controls stayed hidden;
- Settings rendered without repeated helper copy.
