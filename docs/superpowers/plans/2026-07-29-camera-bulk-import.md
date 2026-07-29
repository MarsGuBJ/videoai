# Camera Bulk Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Discover the real channels for all 359 spreadsheet camera rows, import them idempotently into VideoAI, and start only cameras visible in Live Preview.

**Architecture:** A standalone MCP-side import module reads a secret-free CSV manifest, queries Hikvision ISAPI first, falls back to HCNetSDK device channel metadata, maps rows to distinct main-stream channels, and calls the existing backend camera API. Live Preview uses the existing start endpoint for stopped cameras in the current visible window so bulk import does not pull all streams at once.

**Tech Stack:** Python 3.12, HCNetSDK ctypes wrapper, urllib/HTTP Digest, pytest, React/TypeScript, Node test runner, Docker Compose.

---

### Task 1: Add the audited camera manifest

**Files:**
- Create: `mcp-server/app/data/2026-07-29-cameras.csv`
- Create: `mcp-server/tests/test_camera_import.py`

- [ ] **Step 1: Write the failing manifest test**

```python
from pathlib import Path

from app.camera_import import load_camera_rows


def test_manifest_contains_all_spreadsheet_rows():
    path = Path(__file__).parents[1] / "app" / "data" / "2026-07-29-cameras.csv"
    rows = load_camera_rows(path)
    assert len(rows) == 359
    assert len({row.host for row in rows}) == 336
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd mcp-server && python -m pytest tests/test_camera_import.py -q`

Expected: FAIL because `app.camera_import` does not exist.

- [ ] **Step 3: Export only valid camera rows from the supplied workbook**

Create a UTF-8 CSV with columns:

```csv
sequence,name,area,camera_type,device_name,host,sdk_port
292,南面围墙枪机01,赛迪电气/周界,枪机,南面围墙枪机01,10.10.1.20,8000
```

Exclude workbook notes and credentials. Preserve all 359 data rows, including rows with repeated names or hosts.

- [ ] **Step 4: Add the minimal loader**

Create `mcp-server/app/camera_import.py` with `CameraRow` and `load_camera_rows` using `csv.DictReader`. Validate non-empty sequence/name/area/host, valid IPv4 addresses, positive SDK ports, unique `(sequence, name, host)` keys, exactly 359 rows, 336 unique hosts, and 23 duplicate-host groups.

- [ ] **Step 5: Run the manifest test**

Run: `cd mcp-server && python -m pytest tests/test_camera_import.py -q`

Expected: PASS.

### Task 2: Expose HCNetSDK device channels

**Files:**
- Modify: `mcp-server/app/hcnetsdk_playback.py`
- Modify: `mcp-server/tests/test_hcnetsdk_playback.py`

- [ ] **Step 1: Write failing device-channel tests**

```python
from app.hcnetsdk_playback import device_channel_numbers


def test_device_channel_numbers_combines_analog_and_digital_channels():
    assert device_channel_numbers(start_channel=1, analog_count=2, start_digital_channel=33, digital_count=2) == [1, 2, 33, 34]


def test_device_channel_numbers_deduplicates_overlapping_ranges():
    assert device_channel_numbers(start_channel=1, analog_count=1, start_digital_channel=1, digital_count=1) == [1]
```

- [ ] **Step 2: Verify RED**

Run: `cd mcp-server && python -m pytest tests/test_hcnetsdk_playback.py -q`

Expected: FAIL because `device_channel_numbers` is undefined.

- [ ] **Step 3: Implement channel metadata without changing existing login callers**

Replace the opaque leading portion of `NET_DVR_DEVICEINFO_V30` with the official channel-count fields while preserving the structure size. Add:

```python
@dataclass(frozen=True)
class HcNetSdkDeviceSession:
    user_id: int
    channels: tuple[int, ...]


def device_channel_numbers(start_channel: int, analog_count: int, start_digital_channel: int, digital_count: int) -> list[int]:
    analog = range(start_channel, start_channel + analog_count)
    digital = range(start_digital_channel, start_digital_channel + digital_count)
    return sorted(set(analog) | set(digital))
```

Add `login_with_device_info()` returning the login ID and channel tuple. Keep `login()` returning only the integer ID for playback/download compatibility.

- [ ] **Step 4: Verify GREEN and regression tests**

Run: `cd mcp-server && python -m pytest tests/test_hcnetsdk_playback.py -q`

Expected: PASS.

### Task 3: Implement ISAPI discovery, channel mapping, and idempotent import

**Files:**
- Modify: `mcp-server/app/camera_import.py`
- Modify: `mcp-server/tests/test_camera_import.py`

- [ ] **Step 1: Write failing ISAPI parsing tests**

Use fixture XML containing channels `101`, `102`, `201`, and `202`. Assert only main-stream IDs ending in `01` are returned and names are preserved.

- [ ] **Step 2: Write failing mapping tests**

Cover one row/one channel, normal and thermal rows mapped to two distinct channels, ball/PTZ rows mapped by normalized channel names, duplicate display names kept separate by sequence, and ambiguous row/channel counts returned as errors.

- [ ] **Step 3: Write failing idempotent planning tests**

Given existing cameras with `description="camera-import:341"`, assert the planner skips an identical mapping, updates a changed track, and creates a missing row without duplicating import keys.

- [ ] **Step 4: Verify RED**

Run: `cd mcp-server && python -m pytest tests/test_camera_import.py -q`

Expected: FAIL for the missing discovery, mapping, and planner functions.

- [ ] **Step 5: Implement ISAPI and HCNetSDK discovery**

Use HTTP Digest GET against `http://<host>/ISAPI/Streaming/channels`, parse XML by local tag names, and retain main-stream IDs. If ISAPI fails or returns no channels, call `HcNetSdkLibrary.instance().login_with_device_info(host, sdk_port, username, password)`, convert device channel numbers to streaming IDs with `channel * 100 + 1`, then log out.

- [ ] **Step 6: Implement deterministic distinct-channel mapping**

Normalize punctuation and whitespace, score exact/contained camera names, use ordinary/thermal keywords to break dual-spectrum ties, and otherwise accept ordered mapping only when the number of unassigned rows equals the number of unassigned channels. Return an explicit ambiguity record instead of reusing a channel.

- [ ] **Step 7: Implement backend API application and CLI**

Build RTSP URLs as `rtsp://<encoded credentials>@<host>:<discovered RTSP port>/Streaming/Channels/<streaming_id>`. Read credentials from `CAMERA_IMPORT_USERNAME` and `CAMERA_IMPORT_PASSWORD`; never print the URL. Add `--dry-run` and `--apply`, use `VIDEOAI_BACKEND_URL`, and emit a JSON summary containing counts and non-sensitive failures.

- [ ] **Step 8: Verify GREEN**

Run: `cd mcp-server && python -m pytest tests/test_camera_import.py tests/test_hcnetsdk_playback.py -q`

Expected: PASS.

### Task 4: Start only visible cameras in Live Preview

**Files:**
- Modify: `frontend/src/pages/LivePreview/index.tsx`
- Create: `frontend/tests/live-preview-visible-start.test.mjs`

- [ ] **Step 1: Write a failing source contract test**

Assert the page computes stopped cameras from `visibleCameras`, calls `api.startCamera(camera.id)` for those entries, merges successful responses into state, and does not call `stopCamera` when a camera leaves the visible set.

- [ ] **Step 2: Verify RED**

Run: `cd frontend && node --test tests/live-preview-visible-start.test.mjs`

Expected: FAIL because the visible-camera start effect is absent.

- [ ] **Step 3: Implement the minimal visible-camera effect**

Add an effect guarded by a ref-backed set of in-flight camera IDs. Start only visible cameras whose status is not `RUNNING`, merge successful camera responses by ID, clear failed IDs so normal React updates can retry, and cancel state updates after unmount.

- [ ] **Step 4: Verify GREEN and compile**

Run: `cd frontend && node --test tests/live-preview-visible-start.test.mjs && npm run build`

Expected: test PASS and Vite production build succeeds.

### Task 5: Run local regression verification

**Files:**
- No new files.

- [ ] **Step 1: Run MCP tests**

Run: `cd mcp-server && python -m pytest -q`

Expected: all tests pass.

- [ ] **Step 2: Run frontend verification**

Run: `cd frontend && node --test tests/*.test.mjs && npm run build`

Expected: all Node tests and TypeScript/Vite build pass.

- [ ] **Step 3: Run repository checks**

Run: `git diff --check` and `docker compose config --quiet`.

Expected: both commands exit 0.

### Task 6: Deploy, discover, import, and validate

**Files:**
- Remote backup under `/home/public/videoai/backups/<timestamp>/`
- Remote project files corresponding to Tasks 1-4.

- [ ] **Step 1: Verify target connectivity and current service state**

Connect to `public@10.10.3.100`, verify `/home/public/videoai`, `docker compose ps`, and the backend camera count without changing state.

- [ ] **Step 2: Back up current camera storage**

Create a timestamped backup of `/home/public/videoai/storage/cameras` and verify `cameras.json` exists in the backup.

- [ ] **Step 3: Deploy only required files**

Upload the MCP importer/module/tests/data and the Live Preview page/test. Rebuild only `mcp-server` and `frontend`; do not replace remote `.env`, storage, or unrelated compose configuration.

- [ ] **Step 4: Run remote dry-run discovery**

Execute the importer inside `mcp-server` with credentials passed through one-time environment variables and `--dry-run`. Verify totals: 359 input rows, 336 hosts, no duplicate import keys, and review all discovery/mapping failures.

- [ ] **Step 5: Apply the import**

Run the same importer with `--apply`. Verify `created + updated + skipped + failed == 359`, and rerun dry-run to prove idempotency.

- [ ] **Step 6: Validate deployment and video**

Check container health, backend camera count, imported metadata uniqueness, and that initial Live Preview starts only its visible cameras. Sample streams from multiple areas plus at least one dual-channel device; require FLV header `464c5601` and non-zero bytes. Report unreachable or ambiguous devices separately without claiming they were imported.

