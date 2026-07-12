# Databricks Apps Monorepo

This repository demonstrates how to manage **multiple Databricks Apps in a single Git repository** with a clear split between:

- **Controlled environments** (`staging`, `prod`) — deployed automatically by GitHub Actions using a service principal
- **Uncontrolled environments** (`dev`) — deployed manually by individual developers from feature branches

## Repository layout

```text
application_examples/
├── .github/
│   └── workflows/
│       ├── deploy-app.yml            # Shared reusable deploy workflow
│       ├── dummy_app_1-deploy.yml    # Deploy workflow for dummy_app_1 only
│       ├── dummy_app_1-validate.yml  # Validate workflow for dummy_app_1 only
│       ├── dummy_app_2-deploy.yml    # Deploy workflow for dummy_app_2 only
│       └── dummy_app_2-validate.yml  # Validate workflow for dummy_app_2 only
├── dummy_app_1/
│   ├── databricks.yml
│   └── ...
└── dummy_app_2/
    ├── databricks.yml
    └── ...
```

GitHub only loads workflow files from `.github/workflows/` at the **repository root** (symlinks and per-app `.github/` subfolders are not supported). Each app gets its own pair of workflow files at the root, named `<app_folder>-deploy.yml` and `<app_folder>-validate.yml`, with `paths` filters so changes to one app never trigger the other.

## Branch and environment model

| Branch | Bundle target | Workspace | Deployment | App name pattern |
| --- | --- | --- | --- | --- |
| `feature/*` | `dev` | Dev | Manual (`databricks bundle deploy -t dev`) | `dummy-app-{N}-{user}` |
| `staging` | `staging` | Dev | GitHub Actions (auto on push) | `dummy-app-{N}-staging` |
| `prod` | `prod` | Production | GitHub Actions (auto on push) | `dummy-app-{N}-prod` |

The **branch name equals the bundle target and GitHub Environment** for controlled deployments. `deploy-app.yml` derives all three from `github.ref_name` automatically:

```yaml
# Inside deploy-app.yml — no target input needed on push
BUNDLE_TARGET: ${{ inputs.target != '' && inputs.target || github.ref_name }}
environment:   ${{ inputs.target != '' && inputs.target || github.ref_name }}
```

On push to `staging` or `prod`, no target configuration is passed — the branch name is used directly.

### Controlled environments (staging + prod)

1. Create protected branches: `staging` and `prod`
2. Create GitHub Environments named **`staging`** and **`prod`** (names must match branch names)
3. Configure environment secrets in each (see below)
4. Optionally require reviewers on the `prod` environment

Promotion path:

```text
feature/*  →  PR  →  staging  →  PR  →  prod
```

### Uncontrolled environments (dev)

For day-to-day development, each user:

1. Opens the repo in **Databricks Repos** (dev workspace) on their feature branch
2. Deploys manually from the app folder:

```bash
cd dummy_app_1
databricks bundle deploy -t dev
databricks bundle run dummy_app -t dev
```

The `dev` target uses `mode: development` with a user-scoped `root_path`, so each developer gets an isolated app named `dummy-app-1-{short_name}` without colliding with teammates.

## GitHub configuration

### Environments

Create two environments in **Settings → Environments**:

| Environment | Maps to branch | Workspace |
| --- | --- | --- |
| `staging` | `staging` | Dev |
| `prod` | `prod` | Production |

### Secrets (per environment)

Store these as **environment secrets** (not repository secrets) so staging and prod can use different service principals:

| Secret | Purpose |
| --- | --- |
| `DATABRICKS_HOST` | Workspace URL for this environment |
| `DATABRICKS_CLIENT_ID` | Service principal application ID |
| `DATABRICKS_CLIENT_SECRET` | Service principal OAuth secret |
| `GH_PAT` | GitHub PAT for authenticated checkout (repository secret is also fine) |

> **Note:** The [Databricks CI/CD guide](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/cicd-github-actions) recommends GitHub OIDC federation instead of client secrets. This example uses client ID + secret for simplicity. To upgrade later, switch `deploy-app.yml` to `DATABRICKS_AUTH_TYPE: github-oidc` and remove the client secret.

### Variables (optional, per environment)

| Variable | Purpose |
| --- | --- |
| `DUMMY_APP_1_URL` | Smoke-test URL for `dummy-app-1-{staging\|prod}` |
| `DUMMY_APP_2_URL` | Smoke-test URL for `dummy-app-2-{staging\|prod}` |

## Workflows

### Per-app workflows

Each app has its own deploy and validate workflow files at the repository root:

| App | Deploy workflow | Validate workflow | Path filter |
| --- | --- | --- | --- |
| `dummy_app_1` | `.github/workflows/dummy_app_1-deploy.yml` | `.github/workflows/dummy_app_1-validate.yml` | `dummy_app_1/**` |
| `dummy_app_2` | `.github/workflows/dummy_app_2-deploy.yml` | `.github/workflows/dummy_app_2-validate.yml` | `dummy_app_2/**` |

Both deploy and validate workflows use `paths` filters so **only changes within that app's folder** trigger the workflow. A push to `staging` that only touches `dummy_app_1/` deploys `dummy-app-1-staging` and leaves `dummy_app_2` untouched.

### Shared `deploy-app.yml`

Reusable workflow at `.github/workflows/deploy-app.yml` called by each app's `deploy.yml`:

1. Checkout
2. Validate bundle
3. Bind to existing app if needed
4. `bundle deploy`
5. `bundle run` (required — deploy alone does not restart the app)
6. Poll until RUNNING
7. Optional smoke test

All bundle commands run with `working-directory` set to the app path.

## Adding a new app

1. Create a new folder (e.g. `my_new_app/`) with its own `databricks.yml`, `app.py`, `app.yaml`, and `resources/`
2. Use a unique bundle name: `bundle.name: my-new-app`
3. Follow the naming convention: `my-new-app-staging`, `my-new-app-prod`, `my-new-app-{user}` for dev
4. Copy `.github/workflows/dummy_app_1-deploy.yml` and `dummy_app_1-validate.yml` as templates; rename to `my_new_app-deploy.yml` / `my_new_app-validate.yml` and update the app path, app name, and path filters
5. Add an optional `MY_NEW_APP_URL` environment variable for smoke tests

## App naming convention

| App folder | Bundle name | Staging app | Prod app | Dev app (per user) |
| --- | --- | --- | --- | --- |
| `dummy_app_1` | `dummy-app-1` | `dummy-app-1-staging` | `dummy-app-1-prod` | `dummy-app-1-{user}` |
| `dummy_app_2` | `dummy-app-2` | `dummy-app-2-staging` | `dummy-app-2-prod` | `dummy-app-2-{user}` |

## Branch protection recommendations

**`staging`**

- Require pull request before merge
- Require at least 1 approval
- Require `Validate dummy_app_1` or `Validate dummy_app_2` status check (whichever app the PR touches)

**`prod`**

- Require pull request before merge
- Require at least 2 approvals
- Require validation status checks
- Require GitHub Environment approval (configured on the `prod` environment)

## Binding an existing app

If an app already exists in the workspace, bind it once before CI/CD can manage it:

```bash
cd dummy_app_1
databricks bundle deployment bind dummy_app dummy-app-1-staging \
  --target staging --auto-approve
```

The deploy workflow attempts this automatically, but the first bind may need to be done locally if permissions differ.

## References

- [CI/CD for Databricks Apps with GitHub Actions](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/cicd-github-actions)
- Per-app README files under `dummy_app_1/` and `dummy_app_2/` for app-specific details
