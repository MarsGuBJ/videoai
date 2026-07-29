# Remove get_recording_stream MCP Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove `get_recording_stream` from the MCP tool catalog without removing its HTTP compatibility endpoint or implementation.

**Architecture:** FastMCP registration is controlled by the `@mcp.tool()` decorator, while compatibility HTTP routes are registered independently from `register_http_tool_routes()`. Removing only the decorator separates the public MCP catalog from the retained HTTP handler.

**Tech Stack:** Python 3, FastMCP, Starlette, pytest, Docker Compose

---

### Task 1: Lock the API boundary with tests

**Files:**
- Modify: `mcp-server/tests/test_http_routes.py`

- [ ] **Step 1: Add a failing MCP registration test**

```python
def test_get_recording_stream_is_not_registered_as_mcp_tool():
    tool_names = {tool.name for tool in asyncio.run(server.mcp.list_tools())}
    assert "get_recording_stream" not in tool_names
```

- [ ] **Step 2: Add an HTTP compatibility test**

Create a cached `RecordingSegment`, replace `hcnetsdk_playback.start_playback` with a deterministic async function, call `POST /get_recording_stream-http`, and assert status `200`, format `flv`, and the returned URL.

- [ ] **Step 3: Run the registration test and verify RED**

Run: `pytest -q tests/test_http_routes.py::test_get_recording_stream_is_not_registered_as_mcp_tool`

Expected: FAIL because `get_recording_stream` is still present in `mcp.list_tools()`.

### Task 2: Remove only MCP registration

**Files:**
- Modify: `mcp-server/app/server.py:191`

- [ ] **Step 1: Remove the decorator**

Delete only the `@mcp.tool()` line immediately above `get_recording_stream`.

- [ ] **Step 2: Run focused tests and verify GREEN**

Run: `pytest -q tests/test_http_routes.py -k "get_recording_stream"`

Expected: both the MCP exclusion and HTTP compatibility tests pass.

- [ ] **Step 3: Run the full test suite**

Run: `pytest -q`

Expected: all tests pass.

### Task 3: Deploy and verify

**Files:**
- Deploy: `mcp-server/app/server.py`

- [ ] **Step 1: Compare the local pre-change server file with the remote file**

Require matching SHA-256 hashes before uploading, or review differences explicitly.

- [ ] **Step 2: Back up and upload**

Create a timestamped remote backup of `/home/public/videoai/mcp-server/app/server.py`, then upload the local file.

- [ ] **Step 3: Rebuild the MCP container**

Run: `docker compose build --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple mcp-server && docker compose up -d --no-deps mcp-server`

- [ ] **Step 4: Verify the remote contract**

Inside the container, assert `get_recording_stream` is absent from `mcp.list_tools()` and confirm a `POST` route exists at `/get_recording_stream-http`.
