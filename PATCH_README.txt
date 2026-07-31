WARtool v0.8.2 build-fix patch

Cause fixed:
- The v0.8.2 workflow/meta files were updated, but tools/validate_static.py still expected siteVersion 0.8.1 and the old cron spelling.
- Every GitHub Action therefore failed during the validation step before deployment.

Apply:
1. Copy the contents of this ZIP into the connected WarTool repository folder.
2. Replace tools/validate_static.py.
3. Commit and push with GitHub Desktop.

Suggested commit:
Fix v0.8.2 deployment validation
