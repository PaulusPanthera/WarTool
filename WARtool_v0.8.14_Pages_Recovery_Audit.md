# WARtool v0.8.14 — GitHub Pages recovery audit

## Source inspected

The complete uploaded `wartoolv814.zip` project was unpacked and tested as a whole.

## Confirmed application state

- `python tools/validate_static.py`: passed
- `node --check js/app.js`: passed
- `python tools/build_static_site.py`: passed
- 601 scored Pokémon
- 282 evolution lines
- 17,680 ranked hunt groups
- 28 methods
- 1,222 files in the Pages artifact
- approximately 60 MB unpacked
- approximately 2.7 MB as a local gzip-compressed tar archive
- no symbolic links in the artifact
- `index.html` is at the artifact root

The WARtool source, generated data and artifact layout are not the cause of the observed `Deployment cancelled` status.

## Concrete workflow defect found

The uploaded repository still used the older Pages action generation:

- `actions/configure-pages@v5`
- `actions/upload-pages-artifact@v4`
- `actions/deploy-pages@v4`

The GitHub logs showed these Node 20 actions being forced onto Node 24. Current official Marketplace releases are configure-pages v6, upload-pages-artifact v5 and deploy-pages v5.

## Recovery changes

- updates all three official Pages actions to their current Node 24 releases;
- keeps current deployments serialized without cancelling the active deployment;
- raises the deploy action timeout to 30 minutes and the job timeout to 35 minutes;
- tolerates temporary Pages status-query errors for longer;
- prints the repository's Pages `build_type` and source in the build log;
- verifies artifact size, root index and absence of symbolic links before upload;
- keeps the existing 15-minute live-data refresh schedule.

## Remaining external condition

Repository **Settings → Pages → Build and deployment → Source** must be `GitHub Actions`. The workflow can read and print the setting, but the normal `GITHUB_TOKEN` cannot safely change that repository setting.
