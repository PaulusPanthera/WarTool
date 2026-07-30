# WARtool v0.8.2 — automatic live refresh

- The public page now checks `data/live/state.json` every 60 seconds while the tab is visible.
- Returning to the tab triggers an immediate check.
- Requests use a timestamp query and `no-store` to avoid stale GitHub Pages/CDN responses.
- The refresh buttons now perform a real data check.
- The five-minute GitHub schedule is written as an explicit minute list.
- A newer scheduled run no longer cancels an active deployment.

GitHub's scheduler is best-effort, so a run can still be delayed or occasionally skipped. The site will pick up the next successful deployment without requiring a manual page reload.
