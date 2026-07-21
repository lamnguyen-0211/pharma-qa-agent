#!/bin/bash
set -e

echo "=== Harness Initialization ==="

if [ ! -f package.json ]; then
  echo "No package.json found. Expected initial stack: Next.js, TypeScript, PostgreSQL/Prisma, and a server-side AI agent layer."
  echo "Read docs/TECH_STACK.md, then scaffold the application before enabling install/lint/typecheck/test/build checks."
else
  command -v npm >/dev/null 2>&1 || { echo "npm is required but was not found." >&2; exit 1; }
  [ -f package-lock.json ] || { echo "package-lock.json is required for reproducible npm ci." >&2; exit 1; }

  echo "=== Installing dependencies ==="
  npm ci

  echo "=== Lint ==="
  npm run lint

  echo "=== Type-check ==="
  npm run typecheck

  echo "=== Tests ==="
  npm test

  echo "=== Browser E2E ==="
  PLAYWRIGHT_CACHE_ROOT="${PLAYWRIGHT_BROWSERS_PATH:-${XDG_CACHE_HOME:-$HOME/.cache}/ms-playwright}"
  if [ -d "$PLAYWRIGHT_CACHE_ROOT" ] && find "$PLAYWRIGHT_CACHE_ROOT" -type f \( -name chrome-headless-shell -o -name chrome \) -executable -print -quit | grep -q .; then
    npm run test:e2e
  else
    echo "Playwright Chromium is unavailable; run 'npx playwright install chromium' to enable browser E2E checks."
  fi

  echo "=== Production build ==="
  npm run build

  if [ -f src/ai-backend/requirements.txt ]; then
    echo "=== Python AI service ==="
    if command -v python3 >/dev/null 2>&1; then
      AI_PYTHON=python3
      if [ -x src/ai-backend/.venv/bin/python ]; then AI_PYTHON=.venv/bin/python; fi
      if (cd src/ai-backend && "$AI_PYTHON" -c 'import pytest' >/dev/null 2>&1); then
        (cd src/ai-backend && "$AI_PYTHON" -m pytest -q)
      else
        echo "Python AI dependencies are unavailable; install src/ai-backend/requirements.txt to run pytest." >&2
      fi
    else
      echo "Python 3 is required to verify src/ai-backend/." >&2
    fi
  fi

  if [ -f src/backend/pom.xml ]; then
    echo "=== Spring Boot core API ==="
    command -v java >/dev/null 2>&1 || { echo "Java 21 is required to verify src/backend/." >&2; exit 1; }
    command -v mvn >/dev/null 2>&1 || { echo "Maven is required to verify src/backend/." >&2; exit 1; }
    (cd src/backend && mvn test)
  fi
fi

echo "=== Verification Complete ==="
echo ""
echo "Next steps:"
echo "1. Read feature_list.json to see current feature state"
echo "2. Pick ONE unfinished feature to work on"
echo "3. Implement only that feature"
echo "4. Re-run verification before claiming done"
