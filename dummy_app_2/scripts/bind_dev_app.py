"""
One-time setup: bind an existing Databricks App to the bundle resource.

WHY THIS IS NEEDED
------------------
`databricks bundle deploy` decides whether to CREATE (POST) or UPDATE (PATCH)
an app by checking its Terraform state stored in the bundle's root_path in the
workspace. When the app already exists but was never deployed through THIS
bundle (e.g. created manually, from a different machine, or before the state
was established), the state has no entry for it and every deploy fails with:

  409 ALREADY_EXISTS – Failed to create app dummy-app-dev.
                       An app with the same name already exists.

`databricks bundle deployment bind` imports the existing app into the bundle's
Terraform state so all future deploys call PATCH instead of POST.

The CI/CD deploy workflow (.github/workflows/deploy.yml) already performs this
bind automatically on every run, so you normally do NOT need this script. It is
provided for manual/local recovery if you ever need to bind outside CI.

HOW TO RUN
----------
Run from the bundle root (the directory that contains databricks.yml):

    cd <repo-root>/dummy_app
    python scripts/bind_dev_app.py

Requires: Databricks CLI installed and authenticated for the dev workspace
(via `databricks configure`, a CLI profile, or OIDC/SP env vars).

AFTER RUNNING
-------------
Run `databricks bundle deploy -t dev` once to confirm the 409 is gone.
All subsequent local and CI/CD deployments work without re-running this script
because the binding is persisted in the workspace state.
"""

import subprocess
import sys
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────
# Bundle root = the directory that contains databricks.yml. This script lives in
# <bundle-root>/scripts/, so the bundle root is its parent's parent. Resolving it
# dynamically means this works for ANY user, ANY branch, and ANY checkout path —
# no hardcoded /Workspace/Users/... path that breaks when the branch folder changes.
BUNDLE_DIR = str(Path(__file__).resolve().parent.parent)
BUNDLE_TARGET = "dev"
RESOURCE_KEY = "dummy_app"  # key used in resources/app.yml (resources.apps.dummy_app)
APP_NAME = "dummy-app-dev"  # name of the existing Databricks App in the dev workspace
# ──────────────────────────────────────────────────────────────────────────────


def run(cmd: list[str], cwd: str) -> tuple[int, str, str]:
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def main() -> None:
    print("=" * 60)
    print("  dummy-app bundle binding — manual recovery")
    print("=" * 60)
    print(f"\nBundle directory: {BUNDLE_DIR}")

    # 1. Confirm the CLI is available.
    code, out, err = run(["databricks", "version"], cwd=BUNDLE_DIR)
    if code != 0:
        print(f"\n❌ Databricks CLI not found on PATH.\n{err}")
        print("\nInstall: https://docs.databricks.com/dev-tools/cli/install.html")
        sys.exit(1)
    print(f"✅ CLI found: {out}")

    # 2. Confirm the app exists.
    code, out, err = run(
        ["databricks", "apps", "get", APP_NAME, "--output", "JSON"],
        cwd=BUNDLE_DIR,
    )
    if code != 0:
        print(f"\n❌ App '{APP_NAME}' not found in the dev workspace.")
        print("If the app does not exist yet, just run `databricks bundle deploy -t dev`")
        print("and the bundle will create it automatically — no binding needed.")
        sys.exit(0)
    print(f"✅ App '{APP_NAME}' confirmed in workspace.")

    # 3. Run the bind command.
    print(f"\nBinding bundle resource '{RESOURCE_KEY}' → app '{APP_NAME}' …")
    cmd = [
        "databricks",
        "bundle",
        "deployment",
        "bind",
        RESOURCE_KEY,
        APP_NAME,
        "--target",
        BUNDLE_TARGET,
        "--auto-approve",
    ]
    print(f"Command: {' '.join(cmd)}\n")

    code, out, err = run(cmd, cwd=BUNDLE_DIR)

    print("── stdout ──────────────────────────────────────────────")
    print(out or "(empty)")
    print("── stderr ──────────────────────────────────────────────")
    print(err or "(empty)")
    print(f"── exit code: {code} ────────────────────────────────────")

    already_bound = any(
        kw in (out + err).lower() for kw in ("already", "imported", "exists", "bound")
    )

    if code == 0:
        print("\n✅ Binding successful!")
        print("   Now run: databricks bundle deploy -t dev")
        print("   The 409 ALREADY_EXISTS error will not occur again.")
    elif already_bound:
        print("\nℹ️  App is already bound to this bundle (state already contains it).")
        print("   Re-running: databricks bundle deploy -t dev  should succeed.")
    else:
        print("\n❌ Binding failed. Review the output above.")
        print("\nCommon causes:")
        print("  • You don't have CAN_MANAGE permission on the app.")
        print("    Fix: grant yourself CAN_MANAGE in the Apps UI.")
        print("  • The deployment lock is held by another process.")
        print("    Fix: wait for it to expire, or deploy with --force-lock.")
        print("  • The CLI version does not support 'bundle deployment bind'.")
        print("    Fix: upgrade the CLI — databricks/setup-cli@main installs the latest.")
        sys.exit(1)


if __name__ == "__main__":
    main()
