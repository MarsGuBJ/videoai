# Remove get_recording_stream MCP Tool Design

## Goal

Remove `get_recording_stream` from the MCP tool catalog while preserving its existing HTTP compatibility endpoint and implementation.

## Scope

- Remove only the `@mcp.tool()` registration from `get_recording_stream`.
- Keep the `get_recording_stream` function unchanged.
- Keep `get_recording_stream` in `register_http_tool_routes()` so `POST /get_recording_stream-http` remains available.
- Keep current documentation because the HTTP compatibility capability remains supported.

## Verification

- A registration test must prove `mcp.list_tools()` does not include `get_recording_stream`.
- An HTTP route test must prove `/get_recording_stream-http` still returns a playable response.
- The full MCP server test suite must pass before deployment.
- Remote verification must check both the MCP tool catalog and the HTTP route table after rebuilding the container.

## Deployment

Back up the remote `server.py`, upload only files required by this change, rebuild `mcp-server`, and verify the internal service on `192.168.11.194:8097`.
