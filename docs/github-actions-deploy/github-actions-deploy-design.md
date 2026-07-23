# GitHub Actions Self-Hosted Deployment Design

**Date:** 2026-07-23  
**Branch:** `feat/github-actions-self-hosted-deploy`

## Goal

Add a free GitHub Actions CI/CD flow that validates pull requests and deploys the complete Docker Compose application to this machine only after a pull request has been merged into `main`.

## Constraints and decisions

- Pull requests targeting `main` run CI but never deploy.
- Only a `push` to `main` starts deployment. In the normal workflow this push is produced by merging an accepted pull request.
- The deployment job runs on a GitHub Actions self-hosted runner installed on the target machine.
- Pull request code runs on a GitHub-hosted runner, preventing unreviewed code from executing on the deployment host.
- The existing root `docker-compose.yml` remains the deployment definition.
- Deployment uses `docker compose up -d --build --remove-orphans` and never uses `down -v`; named database and Redis volumes therefore remain intact.
- Runtime secrets are stored in GitHub Actions secrets and materialized only in a temporary, mode-600 env file on the runner.
- The workflow must not print secret values or pass them as command-line arguments.
- Deployment is serialized so a newer main deployment cannot race an older one.

## Architecture

```text
Pull request -> GitHub-hosted CI -> review/approval -> merge to main
                                                   |
                                                   v
                                      GitHub Actions deploy job
                                      on self-hosted runner
                                                   |
                                                   v
                         temporary env file + docker compose build/up
                                                   |
                                                   v
                         frontend, core API, AI API, databases, Redis
```

The workflow has two independent triggers:

1. `pull_request` targeting `main` runs reproducible application checks on `ubuntu-latest` without secrets.
2. `push` targeting `main` runs deployment on `[self-hosted, linux, x64]`. The job checks out the merged commit, creates a temporary env file from Actions secrets and variables, invokes the deployment script, and removes the env file in an unconditional cleanup step.

The deployment script is intentionally independent of GitHub Actions. It accepts the Compose env file through `DEPLOY_ENV_FILE`, validates the rendered Compose configuration, rebuilds changed images, starts the complete stack, and waits for the configured container health checks.

## Workflow behavior

The CI job runs:

- `npm ci`
- `npm run lint`
- `npm run typecheck`
- `npm test`
- `npm run build`

The deployment job runs only after `push` to `main`. It uses the repository checkout supplied by the runner and sets a stable Compose project name, `pharma-manager`, so containers and named volumes are managed consistently across deployments.

The workflow grants only `contents: read`. It does not use pull-request secrets, `pull_request_target`, privileged Docker-in-Docker, or automatic branch pushes.

## Environment and secrets

Required repository or environment secret:

- `GEMINI_API_KEY` — server-side model credential used by the AI backend.

Required deployment secret:

- `POSTGRES_PASSWORD` — password shared by the two PostgreSQL services and the application connection strings.

Non-secret deployment variables use the current Compose defaults unless explicitly supplied as GitHub Actions variables. The workflow will pass values for the database user and application tuning variables through the temporary env file so the deployed configuration is explicit and reviewable without storing secrets in Git.

The temporary env file is created under `$RUNNER_TEMP`, is readable only by the runner account, and is deleted with `if: always()` after deployment. The repository `.env.example` remains documentation only and is not used as a production secret source.

## Deployment and failure handling

Before changing containers, the script:

1. verifies that Docker and the Compose plugin are available;
2. verifies the env file exists and is not group/world-readable;
3. runs `docker compose --env-file ... config --quiet`;
4. runs `docker compose ... up -d --build --remove-orphans`.

After startup, it waits for the Compose health checks to report healthy for the services that define health checks. On timeout or command failure, it prints `docker compose ps` and bounded service logs, then exits non-zero so the GitHub job is failed. Existing volumes are preserved. A later rerun of the main deployment is the rollback/recovery mechanism; this change does not introduce image registries or database rollback automation.

## Runner setup

The repository owner must install and register a self-hosted runner on this machine with the labels `self-hosted`, `linux`, and `x64`. The runner account must have permission to invoke Docker, normally by belonging to the `docker` group. The runner should be installed as a service and kept outside the application checkout.

The repository owner must also configure the listed secret(s) under GitHub repository Settings → Secrets and variables → Actions. A GitHub Actions environment named `production` may be used to add approval protection before the deploy job runs.

## Testing and acceptance criteria

- A PR to `main` executes CI on `ubuntu-latest` and has no deployment job.
- A merged PR creates a `push` to `main` and starts exactly one deploy job on the self-hosted runner.
- The deployment job does not start for pushes to feature branches.
- Secret values do not appear in workflow logs or repository files.
- A valid deployment starts all Compose services and preserves named volumes.
- Invalid Compose configuration or an unhealthy service fails the job and emits diagnostic status/log output.
- The workflow YAML parses, the shell script passes shell syntax checking, and the existing project verification commands remain usable.

## Out of scope

- Provisioning the GitHub repository or creating the runner registration token.
- Installing Docker or the GitHub Actions runner service automatically.
- Exposing the application through a public domain, TLS proxy, firewall, or cloud load balancer.
- Publishing images to GHCR.
- Automated database migrations rollback.
