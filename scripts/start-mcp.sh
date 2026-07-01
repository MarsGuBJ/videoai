#!/bin/sh
# Start the VideoAI MCP server
set -e

VENV_PYTHON="/tmp/mcp-env/bin/python"
SERVER_DIR="/home/aipu/videoai/mcp-server"
LOG_FILE="/tmp/mcp-server.log"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: Python venv not found at $VENV_PYTHON"
    exit 1
fi

cd "$SERVER_DIR"
export PATH="$HOME/.local/bin:$PATH"

echo "Starting VideoAI MCP server..."
nohup "$VENV_PYTHON" -m app.server > "$LOG_FILE" 2>&1 &
PID=$!
echo "Started with PID: $PID"
echo "Log: $LOG_FILE"
echo "URL: http://localhost:8091/mcp"
