# Self-hosted Runner Setup

## 1. Install the runner

In GitHub, open Settings → Actions → Runners → New self-hosted runner, select Linux x64, and run GitHub's current generated commands in a dedicated runner directory outside the repository checkout. Do not commit the generated token or `.runner` files.

## 2. Grant Docker access

Ensure the account running the runner service can execute both commands:

```bash
docker version
docker compose version
```

Configure the runner labels to include `self-hosted`, `linux`, and `x64`, then install it as a service.

## 3. Configure Actions secrets

Create a `production` environment and add:

- `GEMINI_API_KEY`
- `POSTGRES_PASSWORD`

Optionally add the repository/environment variable `POSTGRES_USER`. The workflow defaults it to `postgres` when absent.

## 4. Verify the lifecycle

Open a branch, create a pull request to `main`, confirm only the `ci` job runs, merge the pull request, and confirm the resulting `main` push runs `deploy` on this machine. A failed health check should fail the job and show Compose diagnostics without removing named volumes.
