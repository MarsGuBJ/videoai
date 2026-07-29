#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== Python worker syntax =="
python3 -m compileall "$ROOT_DIR/worker/app"

echo "== Frontend lint =="
(cd "$ROOT_DIR/frontend" && npm run lint)

echo "== Frontend build =="
(cd "$ROOT_DIR/frontend" && npm run build)

if command -v mvn >/dev/null 2>&1; then
  echo "== Backend Maven package =="
  (cd "$ROOT_DIR/backend" && mvn -q -DskipTests package)
else
  echo "== Backend Maven package skipped: mvn not found =="
fi

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  echo "== Docker Compose config =="
  (cd "$ROOT_DIR" && docker compose config >/dev/null)
else
  echo "== Docker Compose config skipped: docker not usable =="
fi
