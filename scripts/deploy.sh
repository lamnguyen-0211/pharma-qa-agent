#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"
DEPLOY_ENV_FILE="${DEPLOY_ENV_FILE:?DEPLOY_ENV_FILE must point to a mode-600 Compose env file}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-pharma-manager}"
COMPOSE_WAIT_TIMEOUT="${COMPOSE_WAIT_TIMEOUT:-180}"

cd "$ROOT_DIR"

command -v docker >/dev/null 2>&1 || {
  echo "docker is required on the deployment runner" >&2
  exit 1
}
docker compose version >/dev/null 2>&1 || {
  echo "docker compose is required on the deployment runner" >&2
  exit 1
}
[[ -f "$ROOT_COMPOSE_FILE" ]] || {
  echo "Compose file not found: $ROOT_COMPOSE_FILE" >&2
  exit 1
}
[[ -f "$DEPLOY_ENV_FILE" ]] || {
  echo "Deployment env file not found: $DEPLOY_ENV_FILE" >&2
  exit 1
}

ENV_MODE="$(stat -c '%a' "$DEPLOY_ENV_FILE")"
[[ "$ENV_MODE" == 600 ]] || {
  echo "Deployment env file must have mode 600; found $ENV_MODE" >&2
  exit 1
}

compose=(
  docker compose
  --project-name "$COMPOSE_PROJECT_NAME"
  --env-file "$DEPLOY_ENV_FILE"
  --file "$ROOT_COMPOSE_FILE"
)

print_diagnostics() {
  echo "Deployment diagnostics:" >&2
  "${compose[@]}" ps >&2 || true
  "${compose[@]}" logs --no-color --tail=100 >&2 || true
}

on_exit() {
  status=$?
  if [[ "$status" -ne 0 ]]; then
    print_diagnostics
  fi
  exit "$status"
}
trap on_exit EXIT

"${compose[@]}" config --quiet
"${compose[@]}" up -d --build --remove-orphans --wait --wait-timeout "$COMPOSE_WAIT_TIMEOUT"
"${compose[@]}" ps
