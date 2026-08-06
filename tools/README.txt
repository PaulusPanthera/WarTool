WARtool v0.8.14 maintenance files

- import_google_sheet.py: fetches and validates the two team catch tabs and Settings tab
- rebuild_encounters.py: authoritative site generator; rebuilds rod-specific planner encounter groups from a PokeMMO dump
- validate_static.py: audits the complete project before deployment
- build_static_site.py: creates the GitHub Pages _site artifact
- GOOGLE_SHEET_SETUP.md: Sheet column and validation contract
- data/safari-rates.json: bundled community balls-only Safari capture estimates used by the planner
- data/safety-rules.json: shared context-aware shiny-safety rules used during encounter rebuilds
- shiny_wars_optimizer.py: legacy standalone CSV experiment; not used by the website build
