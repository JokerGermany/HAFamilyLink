# Fork patches

`main` in this fork is generated automatically: **latest `noiwid/HAFamilyLink` main + these patches**.
Do not commit to `main` directly – it is force-rebuilt. Change things here on the `fork-patches` branch.

- `overlay/` – files copied 1:1 into the repo (Steam auth/routes/state, the sync workflow itself)
- `apply.py` – copies the overlay and inserts the Steam router into `familylink-playwright/app/main.py` (anchor-based, idempotent)

The workflow `.github/workflows/sync-upstream.yml` runs daily, on manual trigger and on every push to `fork-patches`.
It needs a repository secret `SYNC_TOKEN` (PAT with `repo` + `workflow` scope).
If `apply.py` fails (upstream moved an anchor), the run fails and `main` stays untouched.
