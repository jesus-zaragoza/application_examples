# dummy_app_2

> **CI/CD workflows** for this repository live at the **repository root** in `.github/workflows/`.
> See the [root README](../README.md) for the monorepo deployment model (staging/prod branches, multi-app matrix, GitHub Environments).

## 1. High-level architecture diagram (ASCII)

```text
                           +----------------------------------+
                           |            GitHub Repo           |
                           | data-analytics-ai-databricks     |
                           | branches: feature/*, dev, main   |
                           +-----------------+----------------+
                                             |
                                             | PR validation / deploy workflows
                                             v
+------------------------+       +-----------+------------+       +------------------------+
| Personal Workspace     |       | GitHub Actions         |       | Dev Workspace          |
| Databricks Repos       |<----->| OIDC -> Service        |-----> | Databricks App         |
| Feature branch coding  |       | Principal auth         |       | dummy-app-dev          |
| PAT acceptable only    |       | Bundle validate/deploy |       | Shared test target     |
| for interactive dev    |       +-----------+------------+       +------------------------+
+------------------------+                   |
                                             |
                                             v
                                     +-------+--------+
                                     | Prod Workspace |
                                     | Databricks App |
                                     | dummy-app-prod |
                                     | Protected env  |
                                     +----------------+
```

## 2. Complete workflow diagram

```text
feature/* branch
  -> developer edits code in Databricks Repos
  -> local test inside personal workspace
  -> push branch to GitHub
  -> optional manual Deploy Dev workflow from feature branch
  -> shared dummy-app-dev updated for branch testing
  -> if rollback needed, redeploy dev branch to dummy-app-dev
  -> create PR into dev
  -> validate.yml runs lint + tests + bundle validation
  -> merge into dev
  -> deploy-dev.yml auto deploys dummy-app-dev
  -> business / QA validation in dev
  -> create PR from dev into main
  -> validate.yml runs again, including prod target validation
  -> merge into main
  -> deploy-prod.yml auto deploys dummy-app-prod
  -> post-deploy smoke test runs
```

## 3. Repository structure

```text
dummy_app/
├── .github/
│   └── workflows/
│       ├── deploy.yml
│       ├── deploy-dev.yml
│       ├── deploy-prod.yml
│       └── validate.yml
├── resources/
│   ├── app.yml
│   └── permissions.yml
├── src/
│   └── dummy_app/
│       ├── __init__.py
│       └── chart.py
├── tests/
│   ├── integration/
│   │   └── test_app_health.py
│   └── unit/
│       └── test_chart.py
├── .gitignore
├── app.py
├── app.yaml
├── databricks.yml
├── manifest.yaml
├── pyproject.toml
├── README.md
├── requirements-dev.txt
└── requirements.txt
```

File-by-file purpose:

* `.github/workflows/validate.yml`: PR validation for linting, formatting, unit tests, bundle schema generation, and bundle validation.
* `.github/workflows/deploy.yml`: reusable deployment workflow used by both dev and prod wrappers.
* `.github/workflows/deploy-dev.yml`: automatic deployment from `dev` plus manual feature-branch deployment to `dummy-app-dev`.
* `.github/workflows/deploy-prod.yml`: automatic deployment from `main` plus controlled manual redeploy for rollback.
* `resources/app.yml`: Databricks App bundle resource with target-driven name and runtime env vars.
* `resources/permissions.yml`: bootstrap manager permission for the bundle.
* `src/dummy_app/chart.py`: testable Python logic separated from Streamlit UI.
* `tests/unit/test_chart.py`: unit tests for the helper module.
* `tests/integration/test_app_health.py`: smoke test that checks the deployed app responds with the expected marker.
* `app.py`: Streamlit entrypoint, renders deployment metadata and sample visualization.
* `app.yaml`: Databricks App process command.
* `databricks.yml`: root Declarative Automation Bundle configuration, targets, and variables.
* `manifest.yaml`: lightweight project metadata retained for future scaffolding and ownership tracking.
* `pyproject.toml`: Ruff and pytest configuration.
* `requirements-dev.txt`: CI-only tools.
* `requirements.txt`: runtime dependencies.

## 4. Git branching strategy

Recommended branch model:

* Long-lived branches:
  * `dev` for the integrated non-production baseline.
  * `main` for production-ready code only.
* Short-lived branches:
  * `feature/<ticket-or-purpose>` created from `dev`.
  * `hotfix/<issue>` created from `main` only for urgent production fixes.

Promotion model:

* `feature/*` -> PR -> `dev`
* `dev` -> PR -> `main`
* `hotfix/*` -> PR -> `main`, then back-merge to `dev`

Why this design:

* It matches your current working model.
* It supports manual feature-branch deployment to the shared dev app.
* It preserves a clear promotion path and rollback point.

## 5. Authentication architecture

Recommended production approach: Databricks service principal with GitHub OIDC workload identity federation.

Authentication comparison:

| Method | Use case | Pros | Cons | Recommendation |
| --- | --- | --- | --- | --- |
| PAT | Personal interactive development | Easy to create and use in Databricks Repos | User-bound, long-lived secret, poor rotation, weak audit boundary | Acceptable only for personal workspace development |
| Service Principal + Client Secret | Basic CI/CD | Non-human identity, better than PAT | Still a long-lived secret in GitHub | Acceptable fallback only if OIDC is unavailable |
| Service Principal + OAuth Machine-to-Machine | Enterprise automation | Strong non-human identity, scoped permissions, standard Databricks recommendation | Requires service principal and OAuth setup | Good baseline |
| GitHub OIDC to Databricks Service Principal | GitHub Actions CI/CD | Short-lived credentials, no stored secret, best auditability, least secret sprawl | Requires federation policy setup | Preferred production implementation |

Recommended split:

* Personal Databricks Workspace / Databricks Repos: developer PAT is acceptable.
* GitHub Actions CI/CD: service principal with GitHub OIDC federation.
* Avoid PATs in CI/CD.
* Avoid sharing one service principal across dev and prod if separate identities are possible.

## 6. GitHub Secrets

Required secrets for the implemented OIDC-based design:

| Name | Needed by | Secret | Purpose |
| --- | --- | --- | --- |
| `DATABRICKS_HOST_DEV` | `validate.yml`, `deploy-dev.yml` | No, but store as secret for simplicity | Dev workspace URL |
| `DATABRICKS_CLIENT_ID_DEV` | `validate.yml`, `deploy-dev.yml` | No, but store as secret for simplicity | Dev CI/CD service principal application ID |
| `DATABRICKS_HOST_PROD` | `validate.yml`, `deploy-prod.yml` | No, but store as secret for simplicity | Prod workspace URL |
| `DATABRICKS_CLIENT_ID_PROD` | `validate.yml`, `deploy-prod.yml` | No, but store as secret for simplicity | Prod CI/CD service principal application ID |

Recommended GitHub Variables:

| Name | Environment | Purpose |
| --- | --- | --- |
| `DATABRICKS_APP_URL_DEV` | dev | URL for `dummy-app-dev` smoke test |
| `DATABRICKS_APP_URL_PROD` | prod | URL for `dummy-app-prod` smoke test |

If you use service principal client secrets instead of OIDC, you would additionally need:

* `DATABRICKS_CLIENT_SECRET_DEV`
* `DATABRICKS_CLIENT_SECRET_PROD`

If you use PAT-based CI/CD, you would instead need:

* `DATABRICKS_TOKEN_DEV`
* `DATABRICKS_TOKEN_PROD`

## 7. Databricks configuration

Workspaces:

* Personal workspace: used only for Databricks Repos development.
* Dev workspace: deployment target for `dummy-app-dev`.
* Prod workspace: deployment target for `dummy-app-prod`.

Bundle target mapping:

* `development` target -> dev workspace -> `dummy-app-dev`
* `production` target -> prod workspace -> `dummy-app-prod`

Resource naming:

* App names are fixed by environment, not by branch.
* Feature branch validation still deploys to `dummy-app-dev` when manually triggered.
* Because `dummy-app-dev` is shared, only one branch deployment should be active at a time.

Databricks Repos guidance:

* Databricks Repos syncs the connected Git branch, not the whole repository history in real time.
* Branch changes are explicit: developers choose branch, pull, commit, and push.
* Databricks Repos does not automatically switch branches for a developer.
* Developers should pull before starting work and before deployment to reduce conflicts.
* Merge conflicts are best resolved in GitHub or directly in the Repo after pulling latest changes.
* Multiple developers stay safe by isolating changes in feature branches and avoiding direct edits on `dev` or `main`.

## 8. Databricks Bundle

Bundle implementation decisions:

* `databricks.yml` remains at repo root because Databricks Apps CI/CD guidance expects a root bundle file.
* `resources/app.yml` contains the Databricks App resource.
* App name is injected from variables so dev and prod use the same definition safely.
* `app_version` and `git_branch` are passed by GitHub Actions using `--var` during deploy.
* `workspace.root_path` is shared instead of user-home scoped so CI/CD is not tied to a specific human identity.
* Permissions are split between a bootstrap manager and target-based app admin/user groups.

Environment-specific values belong in these places:

| Configuration type | Best location |
| --- | --- |
| Workspace host | GitHub secret or variable |
| App URL | GitHub environment variable |
| App name | Bundle target variable |
| Catalog / schema / endpoint names | Bundle target variable |
| Sensitive runtime secrets | Databricks secret scope or app-managed secret source, not GitHub unless absolutely necessary |
| OAuth identity for CI/CD | GitHub OIDC federation + Databricks service principal |

## 9. GitHub Actions YAML files

Workflow intent:

* `validate.yml`: executes on PRs to `dev` and `main`; runs code quality, tests, and bundle validation.
* `deploy-dev.yml`: executes automatically on pushes to `dev`; can also be run manually from a feature branch.
* `deploy-prod.yml`: executes automatically on pushes to `main`; can also be run manually for controlled redeploy.
* `deploy.yml`: reusable workflow centralizing checkout, Databricks auth, validation, deploy, start, summary, and smoke test steps.

## 10. Validation workflow

Validation sequence implemented in `validate.yml`:

1. Checkout repository.
2. Setup Python 3.11.
3. Install runtime and dev dependencies.
4. Check formatting with `ruff format --check`.
5. Run lint rules with `ruff check`.
6. Run unit tests with `pytest tests/unit -q`.
7. Setup Databricks CLI.
8. Generate bundle schema JSON.
9. Run `databricks bundle validate -t development`.
10. For PRs into `main`, also validate `production`.

Why this design:

* Fail fast on code quality before Databricks validation.
* Validate both targets before higher-environment promotion.
* Keep validation reproducible in GitHub and developer workstations.

## 11. Deployment workflow

Development deployment:

* Merge to `dev` triggers `deploy-dev.yml` automatically.
* A developer can manually trigger `deploy-dev.yml` from a feature branch to test the branch in `dummy-app-dev`.
* The workflow passes `github.sha` into `app_version` so the running app shows exactly what commit is deployed.
* Post-deploy smoke test checks for the `Dummy App Ready` marker.

Production deployment:

* Merge to `main` triggers `deploy-prod.yml` automatically.
* The reusable workflow sets `environment: prod`, so GitHub Environment approval rules can block deployment until approved.
* Same deployment flow is reused to keep prod behavior consistent with dev.

## 12. Rollback workflow

Rollback scenarios:

* Failed feature-branch dev deploy:
  * Run `deploy-dev.yml` again and deploy `dev` branch.
  * This restores `dummy-app-dev` to the integrated baseline.
* Failed merge-to-dev deploy:
  * Revert commit in GitHub, merge revert into `dev`, auto redeploy to dev.
* Failed production deploy:
  * Revert the merge in `main`, then let `deploy-prod.yml` redeploy.
  * For urgent rollback, manually run `deploy-prod.yml` with the last known good tag or SHA.
* Emergency hotfix:
  * Create `hotfix/*` from `main`, validate, merge into `main`, deploy, and back-merge into `dev`.

Note: Declarative Automation Bundles do not provide a one-click historical rollback artifact. The rollback unit is Git history plus redeployment.

## 13. Security architecture

Security controls to enforce:

* Use separate service principals for dev and prod if possible.
* Grant CI/CD principals only the permissions required to deploy and manage the app.
* Use GitHub OIDC instead of stored client secrets where possible.
* Put prod deployment behind GitHub Environment approvals.
* Use least privilege on Unity Catalog objects, serving endpoints, and AI Search assets.
* Keep app runtime secrets in Databricks-managed secret locations, not in source control.
* Do not use personal tokens in GitHub Actions.
* Restrict `CAN_MANAGE` to a small admin group; give broader audiences only `CAN_USE`.

## 14. Monitoring

Monitor the following layers:

* GitHub Actions runs for validation and deployments.
* Databricks CLI deployment output from `bundle deploy` and `bundle summary`.
* Databricks App state and application logs in the workspace.
* Model Serving endpoint status and inference metrics if the app calls a model.
* AI Search endpoint latency and errors if vector retrieval is used.
* GitHub Environment approval and audit trail for prod.

Recommended alerts:

* Failed validation workflow.
* Failed dev deployment.
* Failed prod deployment.
* App health smoke test failure.
* Serving endpoint not READY.
* AI Search endpoint or index access failure.

## 15. Production best practices

* Use explicit environment names and fixed app names by environment.
* Keep bundle resources modular under `resources/`.
* Separate UI code from testable business logic under `src/`.
* Pin dependency major/minor versions.
* Require PR review into `dev` and `main`.
* Require status checks for validation before merge.
* Protect `main` with required reviewers and environment approval.
* Use release tags for production traceability.
* Add release notes for every promotion from `dev` to `main`.
* Document rollback steps before go-live.

## 16. Complete end-to-end example from developer commit to production deployment

1. Developer creates `feature/add-feedback-panel` from `dev`.
2. Developer opens the branch in Databricks Repos inside the personal workspace.
3. Developer updates `app.py` or code in `src/`.
4. Developer tests interactively in the personal workspace.
5. Developer commits and pushes to GitHub.
6. Developer manually runs `deploy-dev.yml` from that feature branch to deploy branch code into `dummy-app-dev`.
7. Developer validates behavior in dev.
8. If the branch deployment is bad, developer re-runs `deploy-dev.yml` using `dev` branch to restore the shared app.
9. If good, developer opens a PR from feature branch into `dev`.
10. `validate.yml` runs.
11. After approval, PR is merged into `dev`.
12. `deploy-dev.yml` auto deploys the integrated `dev` branch to `dummy-app-dev`.
13. Team performs QA/UAT in dev.
14. A PR from `dev` into `main` is opened.
15. `validate.yml` runs again, now including production target validation.
16. After approval, merge to `main` happens.
17. `deploy-prod.yml` starts.
18. GitHub Environment protection pauses until approved.
19. Deployment proceeds to `dummy-app-prod`.
20. Smoke test runs against the production app URL.

## 17. Common mistakes and troubleshooting

Common mistakes:

* Using PATs in CI/CD instead of service principal federation.
* Letting multiple developers deploy different feature branches into `dummy-app-dev` simultaneously.
* Storing environment-specific names directly in app code instead of bundle variables.
* Deploying to prod from anything other than `main` or a controlled release SHA.
* Forgetting to grant the service principal permissions in Databricks.
* Forgetting GitHub `id-token: write` permission for OIDC.

Troubleshooting quick guide:

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `bundle validate` auth failure | OIDC federation not configured or wrong client ID | Recheck federation policy, workspace host, and client ID |
| Deployment succeeds but app fails to start | App command or dependencies invalid | Review app logs and validate `requirements.txt` and `app.yaml` |
| Smoke test fails | App not yet warm or URL not reachable | Increase retry window or verify URL and access model |
| Feature deploy overwrote another test | Shared `dummy-app-dev` target | Coordinate use of the shared dev app or add preview apps later |
| Prod deploy blocked | GitHub Environment approval required | Approve in GitHub or update protection rules |
| Repo out of date in Databricks Repos | Developer did not pull latest changes | Pull latest branch state before editing or deploying |

## 18. Final checklist before going live

* Create dev and prod Databricks service principals.
* Configure GitHub OIDC federation for both service principals.
* Grant the service principals permissions to deploy and manage the target app.
* Replace `<prod-workspace-url>` in `databricks.yml`.
* Create GitHub secrets: `DATABRICKS_HOST_DEV`, `DATABRICKS_CLIENT_ID_DEV`, `DATABRICKS_HOST_PROD`, `DATABRICKS_CLIENT_ID_PROD`.
* Create GitHub variables: `DATABRICKS_APP_URL_DEV`, `DATABRICKS_APP_URL_PROD`.
* Configure GitHub branch protection for `dev` and `main`.
* Configure GitHub Environment protections for `prod` and optionally `dev`.
* Confirm the app admin and user groups exist in each workspace.
* Replace placeholder catalog, schema, and optional AI endpoint names in `databricks.yml` target variables.
* Run `validate.yml` on a test PR.
* Run a manual feature-branch deployment to `dummy-app-dev`.
* Merge into `dev` and verify automatic deployment.
* Merge into `main` and verify production approval and deployment.
* Document operational ownership and rollback approvers.

## Branch protection recommendations

Configure GitHub as follows:

* `dev`
  * Require pull request before merge.
  * Require at least 1 approval.
  * Require `Validate Databricks App Bundle` status check.
  * Block direct pushes except for admins if policy allows.
* `main`
  * Require pull request before merge.
  * Require at least 2 approvals.
  * Require successful validation checks.
  * Require linear history.
  * Block direct pushes.
  * Require conversation resolution.
  * Optionally require signed commits.

## Notes on developer experience

* Developers keep a simple workflow in Databricks Repos.
* Manual feature-branch deployment gives fast feedback without waiting for merge.
* Dev and prod stay consistent because the same reusable deployment workflow is used for both.
* The only intentional trade-off is that `dummy-app-dev` is a shared deployment slot, so usage needs light coordination.
