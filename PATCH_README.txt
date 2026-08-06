WARtool v0.8.14 GitHub Pages recovery patch

Contains only:
- .github/workflows/deploy-pages.yml
- tools/validate_static.py
- WARtool_v0.8.14_Pages_Recovery_Audit.md

Apply:
1. Copy these files into the connected WarTool repository.
2. Replace the two existing matching files.
3. Commit: Upgrade Pages deployment actions and recovery checks
4. Push origin once.
5. Do not re-run any older failed workflow run.

The new push creates a fresh commit SHA and a fresh Pages deployment.
Repository Settings > Pages > Source must be GitHub Actions.
