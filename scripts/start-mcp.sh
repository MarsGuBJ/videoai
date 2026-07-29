#!/bin/sh
# Start the VideoAI MCP server.
#
# Configuration sources (highest priority first):
#   1. Already-exported shell env (e.g. VIDEOAI_BACKEND_URL=... ./start-mcp.sh)
#   2. Repo-root .env file (translates ZLM_HTTP_URL / ZLM_PUBLIC_HTTP_URL /
#      BACKEND_PUBLIC_URL / BACKEND_INTERNAL_URL / ZLM_RTMP_PUSH_BASE /
#      ZLM_SECRET into the VIDEOAI_* names that mcp-server/app/settings.py reads)
#   3. Built-in defaults (assume backend-lite on 8081, ZLM on 81, MCP on 8091)
#
# Required (or defaulted):
#   VIDEOAI_BACKEND_URL          - URL MCP uses to call backend-lite
#                                  (e.g. http://localhost:8081)
#   VIDEOAI_ZLM_HTTP_URL         - URL MCP uses to call ZLMediaKit's control API
#                                  (e.g. http://localhost:81)
#   VIDEOAI_ZLM_PUBLIC_HTTP_URL  - URL returned to clients for /live/... HLS/FLV
#                                  streams (must be reachable from clients, e.g.
#                                  http://192.168.11.194:81)
#   VIDEOAI_ZLM_RTMP_PUSH_BASE   - RTMP target used by media_proxy for NVR
#                                  recording push (e.g. rtmp://localhost/live)
#
# Optional:
#   VIDEOAI_MCP_HOST             - bind address (default 0.0.0.0)
#   VIDEOAI_MCP_PORT             - bind port    (default 8091)
#   VIDEOAI_MCP_TRANSPORT        - streamable-http | sse | stdio
#                                  (default streamable-http)
#
# The script stops any previous MCP process recorded in $PID_FILE before
# starting a new one, so re-running it always reloads the latest code and env.

set -eu

REPO_ROOT="${REPO_ROOT:-/home/aipu/videoai}"
VENV_PYTHON="${VENV_PYTHON:-/tmp/mcp-env/bin/python}"
SERVER_DIR="${SERVER_DIR:-$REPO_ROOT/mcp-server}"
LOG_FILE="${LOG_FILE:-/tmp/mcp-server.log}"
PID_FILE="${PID_FILE:-/tmp/mcp-server.pid}"

# 1. Load .env (if present). set -a exports every assignment below it.
if [ -f "$REPO_ROOT/.env" ]; then
    set -a
    # shellcheck disable=SC1090
    . "$REPO_ROOT/.env"
    set +a
fi

# 2. Translate .env names → MCP's VIDEOAI_* env names.
#    Use already-exported VIDEOAI_* values as the highest-priority source.
: "${VIDEOAI_BACKEND_URL:=${BACKEND_INTERNAL_URL:-${BACKEND_PUBLIC_URL:-http://localhost:8081}}}"
: "${VIDEOAI_ZLM_HTTP_URL:=${ZLM_HTTP_URL:-http://localhost:81}}"
: "${VIDEOAI_ZLM_PUBLIC_HTTP_URL:=${ZLM_PUBLIC_HTTP_URL:-$VIDEOAI_ZLM_HTTP_URL}}"
: "${VIDEOAI_ZLM_RTMP_PUSH_BASE:=${ZLM_RTMP_PUSH_BASE:-rtmp://localhost/live}}"
: "${VIDEOAI_ZLM_SECRET:=${ZLM_SECRET:-035c73f7-bb6b-4889-a715-d9eb2d1925cc}}"
: "${VIDEOAI_MCP_HOST:=0.0.0.0}"
: "${VIDEOAI_MCP_PORT:=8091}"
: "${VIDEOAI_MCP_TRANSPORT:=streamable-http}"

export VIDEOAI_BACKEND_URL
export VIDEOAI_ZLM_HTTP_URL
export VIDEOAI_ZLM_PUBLIC_HTTP_URL
export VIDEOAI_ZLM_RTMP_PUSH_BASE
export VIDEOAI_ZLM_SECRET
export VIDEOAI_MCP_HOST
export VIDEOAI_MCP_PORT
export VIDEOAI_MCP_TRANSPORT

# 2b. Detect docker-style service names that won't resolve on a host install.
warn_if_docker_name() {
    case "$1" in
        http://backend|http://zlm|http://worker|http://triton|http://postgres|http://zlm:*|http://backend:*|http://worker:*|http://triton:*|http://postgres:*)
            echo "  WARNING: $2=$1 looks like a docker-compose service name." >&2
            echo "           If MCP runs on the host, override it with the host-reachable URL, e.g.:" >&2
            echo "             VIDEOAI_ZLM_PUBLIC_HTTP_URL=http://192.168.11.194:81 $0" >&2
            ;;
    esac
}
warn_if_docker_name "$VIDEOAI_BACKEND_URL" "VIDEOAI_BACKEND_URL"
warn_if_docker_name "$VIDEOAI_ZLM_HTTP_URL" "VIDEOAI_ZLM_HTTP_URL"
warn_if_docker_name "$VIDEOAI_ZLM_PUBLIC_HTTP_URL" "VIDEOAI_ZLM_PUBLIC_HTTP_URL"

# 3. Sanity checks.
if [ ! -x "$VENV_PYTHON" ]; then
    echo "Error: Python venv not found at $VENV_PYTHON" >&2
    echo "  Set VENV_PYTHON to your venv's python, e.g.:" >&2
    echo "  VENV_PYTHON=/path/to/.venv/bin/python $0" >&2
    exit 1
fi
if [ ! -d "$SERVER_DIR" ]; then
    echo "Error: mcp-server directory not found: $SERVER_DIR" >&2
    exit 1
fi

# 4. Stop the previous instance, if any.
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null || true)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Stopping previous MCP (pid=$OLD_PID)..."
        kill "$OLD_PID" 2>/dev/null || true
        # Wait up to 5s for graceful shutdown.
        i=0
        while [ "$i" -lt 5 ] && kill -0 "$OLD_PID" 2>/dev/null; do
            sleep 1
            i=$((i + 1))
        done
        if kill -0 "$OLD_PID" 2>/dev/null; then
            kill -9 "$OLD_PID" 2>/dev/null || true
        fi
    fi
    rm -f "$PID_FILE"
fi

# 5. Launch.
cd "$SERVER_DIR"
export PATH="$HOME/.local/bin:$PATH"

echo "Starting VideoAI MCP server..."
echo "  backend         = $VIDEOAI_BACKEND_URL"
echo "  zlm http        = $VIDEOAI_ZLM_HTTP_URL"
echo "  zlm public http = $VIDEOAI_ZLM_PUBLIC_HTTP_URL"
echo "  zlm rtmp push   = $VIDEOAI_ZLM_RTMP_PUSH_BASE"
echo "  mcp bind        = $VIDEOAI_MCP_HOST:$VIDEOAI_MCP_PORT ($VIDEOAI_MCP_TRANSPORT)"

# Truncate the log so the new run is easy to read.
: > "$LOG_FILE"
nohup "$VENV_PYTHON" -m app.server >> "$LOG_FILE" 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"

echo "Started with PID: $NEW_PID"
echo "Log:  $LOG_FILE"
echo "URL:  http://localhost:$VIDEOAI_MCP_PORT/mcp"
