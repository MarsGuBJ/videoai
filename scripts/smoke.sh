#!/usr/bin/env bash
set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://localhost:8081}"
WORKER_URL="${WORKER_URL:-http://localhost:8090}"
TRITON_URL="${TRITON_URL:-http://localhost:8000}"
ZLM_URL="${ZLM_URL:-http://localhost:8080}"

curl -fsS "$BACKEND_URL/api/health"
echo
curl -fsS "$WORKER_URL/health"
echo
curl -fsS "$TRITON_URL/v2/health/ready"
echo
curl -fsS "$ZLM_URL/index/api/getApiList" >/dev/null
echo "smoke ok"

