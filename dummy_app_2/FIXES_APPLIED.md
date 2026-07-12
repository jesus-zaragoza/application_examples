# Fixes Applied to dummy_app CI/CD

## Issue timeline
1. First: 409 ALREADY_EXISTS  → fixed by delete/bind (state issue).
2. Then: empty source_code_path → fixed by hardcoded-path removal + sync block.
3. Now: "No active deployment" / empty Source / 502 → fixed here.

## Root cause of the 502 + empty Source (this round)

A Databricks App has TWO separate operations, and `bundle deploy` only does #1:

    1. bundle deploy    → uploads files to ${workspace.file_path} AND registers
                          the app RESOURCE.                              ✅ done
    2. app deployment   → creates an ACTIVE DEPLOYMENT that loads the uploaded
                          source and starts the container.               ❌ was missing

Your app showed:
    Source:  "No source code — Deploy or link a workspace folder"
    Status:  "No active deployment. Deploy your application..."
    Browser: 502 App Not Available

That is the signature of a registered-but-never-deployed app: the resource
exists, files are uploaded, but no active deployment was ever created, so no
container is running to serve traffic.

## The fix

### .github/workflows/deploy.yml
- Clarified that `bundle deploy` only uploads + registers; it does not start the app.
- Kept the `databricks bundle run dummy_app` step (this performs the app
  deployment against the synced source and starts the container — the step that
  makes Source non-empty and status RUNNING).
- Added a "Verify app reached RUNNING state" step that polls
  `databricks apps get <name>` and FAILS the job if the app does not become
  RUNNING (so a 502 no longer hides behind a green pipeline), printing the app
  JSON + a pointer to the app logs for diagnosis.
- Made the bundle summary step run with `if: always()` so you still get output
  even when verification fails.

Everything else from the previous fix round is retained:
- sync: block uploads app.py, app.yaml, requirements.txt, src/** to files root.
- source_code_path: ${workspace.file_path} for both dev and prod.
- app.py has a defensive sys.path insert so `from src.dummy_app...` resolves.
- bind logic prevents 409 when the app already exists.

## FIX YOUR CURRENTLY-STUCK APP RIGHT NOW (no CI needed)

From the bundle root (the folder containing databricks.yml), authenticated to
the dev workspace:

    databricks bundle deploy -t dev          # re-upload files + register resource
    databricks bundle run    dummy_app -t dev   # <-- THIS creates the active deployment

Then reload the app page. Source should now show the files, status should move
to RUNNING, and the URL should stop returning 502.

If `bundle run` errors, run an explicit app deploy instead:

    # Get the exact source path the bundle uploaded to:
    databricks bundle summary -t dev | grep -i source

    # Deploy the app from that path (example path shown; use the one from summary):
    databricks apps deploy dummy-app-dev \
      --source-code-path /Workspace/Users/<you>/.bundle/dummy-app/dev/files

## How to confirm success

    databricks apps get dummy-app-dev --output json

Look for:  "compute_status": { "state": "RUNNING" }
and a non-empty active deployment / source path.

## If it STILL 502s after an active deployment exists

The app started but the process crashed. Check the app's own logs:
    Workspace UI → Compute → Apps → dummy-app-dev → Logs

Most common causes:
  - A dependency missing from requirements.txt (import error at startup).
  - The Streamlit command in app.yaml failing (check the exact command).
  - App not binding to 0.0.0.0:8000 (already configured correctly here).
