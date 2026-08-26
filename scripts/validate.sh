#!/usr/bin/env bash
# 本地/CI 统一验证入口。
#
# 前置依赖：
#   - Python 门禁：各服务先 `python -m pip install -r <service>/requirements-dev.txt`
#     （提供 pytest、pytest-cov、ruff、mypy；pip-audit 为可选项）。
#   - 前端门禁：frontend 目录先 `npm install`。
#   - backend Maven、docker compose 为可选项，缺失时自动跳过。
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Windows 上 python3 可能是商店占位 stub，须实跑验证可用性
PYTHON="${PYTHON:-}"
if [ -z "$PYTHON" ]; then
  for candidate in python python3; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "" >/dev/null 2>&1; then
      PYTHON="$candidate"
      break
    fi
  done
fi
if [ -z "$PYTHON" ]; then
  echo "error: no working python interpreter found" >&2
  exit 1
fi

echo "== Python worker syntax =="
"$PYTHON" -m compileall "$ROOT_DIR/worker/app"

# Python 三服务门禁：ruff lint/format + pytest（覆盖率阈值见各服务 pyproject.toml
# [tool.coverage.report] fail_under，任一失败即非零退出）。
PYTHON_SERVICES=(backend-lite mcp-server worker)
for service in "${PYTHON_SERVICES[@]}"; do
  echo "== $service: ruff check =="
  (cd "$ROOT_DIR/$service" && "$PYTHON" -m ruff check .)
  echo "== $service: ruff format --check =="
  (cd "$ROOT_DIR/$service" && "$PYTHON" -m ruff format --check .)
  echo "== $service: pytest --cov =="
  (cd "$ROOT_DIR/$service" && "$PYTHON" -m pytest --cov)
done

# 依赖漏洞审计（门禁外，手动执行；已知漏洞清单见阶段 4 整改回报，
# 升级依赖属行为风险，需单独评估后再决定是否纳入门禁）：
#   for service in backend-lite mcp-server worker; do
#     "$PYTHON" -m pip_audit -r "$ROOT_DIR/$service/requirements.txt"
#   done

if (cd "$ROOT_DIR/frontend" && npm run | grep -qE "^  lint$"); then
  echo "== Frontend lint =="
  (cd "$ROOT_DIR/frontend" && npm run lint)
else
  echo "== Frontend lint skipped: no lint script in frontend/package.json =="
fi

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
