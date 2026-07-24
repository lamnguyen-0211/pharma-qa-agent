#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf -- "$WORK_DIR"' EXIT

mkdir -p "$WORK_DIR/bin"
cat >"$WORK_DIR/bin/docker" <<'FAKE_DOCKER'
#!/usr/bin/env bash
set -Eeuo pipefail

printf '%s\n' "$*" >>"$FAKE_DOCKER_LOG"
if [[ "${1:-}" == compose && "${2:-}" == version ]]; then
  exit 0
fi
if [[ "${FAKE_DOCKER_FAIL_UP:-0}" == 1 ]]; then
  for argument in "$@"; do
    [[ "$argument" == up ]] && exit 1
  done
fi
exit 0
FAKE_DOCKER
chmod +x "$WORK_DIR/bin/docker"

printf 'GEMINI_API_KEY=ci-test-key\nPOSTGRES_PASSWORD=ci-test-password\n' >"$WORK_DIR/deploy.env"
chmod 600 "$WORK_DIR/deploy.env"
printf 'services: {}\n' >"$WORK_DIR/alternate-compose.yml"

EXPECTED_COMPOSE_PREFIX="compose --project-name ci-test --env-file $WORK_DIR/deploy.env --file $ROOT_DIR/docker-compose.yml"

env -u COMPOSE_WAIT_TIMEOUT \
  FAKE_DOCKER_LOG="$WORK_DIR/success.log" \
  PATH="$WORK_DIR/bin:$PATH" \
  DEPLOY_ENV_FILE="$WORK_DIR/deploy.env" \
  COMPOSE_PROJECT_NAME="ci-test" \
  COMPOSE_FILE="$WORK_DIR/alternate-compose.yml" \
  "$ROOT_DIR/scripts/deploy.sh"

grep -Fxq "$EXPECTED_COMPOSE_PREFIX config --quiet" "$WORK_DIR/success.log"
grep -Fxq "$EXPECTED_COMPOSE_PREFIX up -d --build --remove-orphans --wait --wait-timeout 180" "$WORK_DIR/success.log"
grep -Fxq "$EXPECTED_COMPOSE_PREFIX ps" "$WORK_DIR/success.log"

chmod 644 "$WORK_DIR/deploy.env"
if env -u COMPOSE_WAIT_TIMEOUT \
  FAKE_DOCKER_LOG="$WORK_DIR/mode.log" \
  PATH="$WORK_DIR/bin:$PATH" \
  DEPLOY_ENV_FILE="$WORK_DIR/deploy.env" \
  COMPOSE_PROJECT_NAME="ci-test" \
  "$ROOT_DIR/scripts/deploy.sh" 2>"$WORK_DIR/mode.err"; then
  echo "expected mode-644 env file to be rejected" >&2
  exit 1
fi
grep -Fq 'Deployment env file must have mode 600; found 644' "$WORK_DIR/mode.err"
chmod 600 "$WORK_DIR/deploy.env"

if FAKE_DOCKER_FAIL_UP=1 \
  FAKE_DOCKER_LOG="$WORK_DIR/failure.log" \
  PATH="$WORK_DIR/bin:$PATH" \
  DEPLOY_ENV_FILE="$WORK_DIR/deploy.env" \
  COMPOSE_PROJECT_NAME="ci-test" \
    "$ROOT_DIR/scripts/deploy.sh"; then
  echo "expected deployment failure was not reported" >&2
  exit 1
fi

grep -Fq 'ps' "$WORK_DIR/failure.log"
grep -Fq 'logs --no-color --tail=100' "$WORK_DIR/failure.log"
echo "deploy script tests passed"
