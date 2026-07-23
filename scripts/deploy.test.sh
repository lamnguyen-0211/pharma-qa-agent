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

FAKE_DOCKER_LOG="$WORK_DIR/success.log" \
PATH="$WORK_DIR/bin:$PATH" \
DEPLOY_ENV_FILE="$WORK_DIR/deploy.env" \
COMPOSE_PROJECT_NAME="ci-test" \
  "$ROOT_DIR/scripts/deploy.sh"

grep -Fq 'config --quiet' "$WORK_DIR/success.log"
grep -Fq 'up -d --build --remove-orphans --wait' "$WORK_DIR/success.log"

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
