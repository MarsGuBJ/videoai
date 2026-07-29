# On-Demand H.264 Live Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing browser live-preview URL start and share a ZLMediaKit-managed H.265-to-H.264 relay on demand, then stop it 60 seconds after the last viewer disconnects.

**Architecture:** Add a small backend relay manager that owns ZLMediaKit `addFFmpegSource`/`delFFmpegSource` calls and per-stream viewer state. Keep raw camera streams untouched; the existing `/api/live/{stream}.live.flv` route proxies a derived `preview-{stream}` H.264 stream while preserving its public contract. Configure a dedicated low-latency FFmpeg command inside the remote ZLMediaKit instance.

**Tech Stack:** Python 3.12, FastAPI, urllib, threading, pytest, ZLMediaKit HTTP API, FFmpeg/libx264, Docker Compose

---

## File Structure

- Create `backend-lite/preview_relay.py`: ZLM API client, relay lifecycle state, viewer reference counting, and idle cleanup.
- Create `backend-lite/tests/test_preview_relay.py`: unit tests for API parameters, relay sharing, cleanup, failures, and credential-safe errors.
- Create `backend-lite/tests/test_live_preview_route.py`: route-level tests for camera validation, derived upstream URL, and release behavior.
- Create `backend-lite/tests/test_deployment_config.py`: deployment contract tests for Compose and environment defaults.
- Create `backend-lite/requirements-dev.txt`: reproducible backend test dependencies.
- Create `backend-lite/pytest.ini`: backend-lite test discovery and import path.
- Modify `backend-lite/main.py`: configure and instantiate the relay manager, integrate the FLV route, and clean relays on camera stop/delete and application shutdown.
- Modify `backend-lite/Dockerfile`: copy the new relay module into the backend image.
- Modify `docker-compose.yml`: inject preview relay settings and enforce the existing single-worker runtime requirement.
- Modify `.env.example`: document non-secret preview relay settings.
- Modify `docs/remote-deployment.md`: document ZLM command configuration and operational verification.
- Modify remote `/data/cloud-edge-platform/midware/zlmmediakit/config.ini`: add the dedicated FFmpeg command key used by the backend.

### Task 1: Add Relay Manager Tests And Test Dependencies

**Files:**
- Create: `backend-lite/requirements-dev.txt`
- Create: `backend-lite/pytest.ini`
- Create: `backend-lite/tests/test_preview_relay.py`
- Test: `backend-lite/tests/test_preview_relay.py`

- [ ] **Step 1: Add the development requirements**

```text
-r requirements.txt
pytest==8.3.5
```

- [ ] **Step 2: Write failing API client tests**

Add the backend test configuration:

```ini
[pytest]
pythonpath = .
testpaths = tests
```

Create fake URL responses that capture requested URLs and return JSON. Assert that `ZlmPreviewClient.start()`:

```python
client = ZlmPreviewClient(
    base_url="http://zlm:82",
    secret="secret-value",
    preview_rtmp_base="rtmp://127.0.0.1/live",
    command_key="ffmpeg.cmd_preview_h264",
    timeout_ms=15_000,
    opener=fake_opener,
)

key = client.start(
    stream_name="camera-1",
    source_url="rtsp://admin:password@10.10.0.93/Streaming/Channels/101",
)

assert key == "source-key-1"
assert requested_path == "/index/api/addFFmpegSource"
assert requested_query["src_url"] == ["rtsp://admin:password@10.10.0.93/Streaming/Channels/101"]
assert requested_query["dst_url"] == ["rtmp://127.0.0.1/live/preview-camera-1"]
assert requested_query["ffmpeg_cmd_key"] == ["ffmpeg.cmd_preview_h264"]
assert requested_query["enable_hls"] == ["0"]
assert requested_query["enable_mp4"] == ["0"]
```

Also assert that `stop("source-key-1")` calls `/index/api/delFFmpegSource`, and that non-zero ZLM responses raise `PreviewRelayError` without including `password` or the source URL in `str(error)`.

- [ ] **Step 3: Write failing lifecycle tests**

Use a fake client and fake timer factory. Cover these independent behaviors:

```python
assert manager.acquire("camera-1", source_url) == "http://zlm:82/live/preview-camera-1.live.flv"
assert fake_client.started == [("camera-1", source_url)]

manager.acquire("camera-1", source_url)
assert fake_client.started == [("camera-1", source_url)]
assert manager.viewer_count("camera-1") == 2

manager.release("camera-1")
manager.release("camera-1")
assert fake_timer.delay == 60
fake_timer.fire()
assert fake_client.stopped == ["source-key-1"]
```

Add separate tests proving that reacquiring cancels the idle timer, `stop_stream()` deletes immediately, `shutdown()` deletes every managed source once, and a failed first start leaves no reusable state.

- [ ] **Step 4: Run the focused tests and verify RED**

Run:

```powershell
rtk python -m pytest -c backend-lite/pytest.ini backend-lite/tests/test_preview_relay.py -q
```

Expected: collection fails with `ModuleNotFoundError: No module named 'preview_relay'`.

- [ ] **Step 5: Commit the failing tests**

```powershell
rtk git add backend-lite/requirements-dev.txt backend-lite/pytest.ini backend-lite/tests/test_preview_relay.py
rtk git commit -m "test: specify on-demand preview relay lifecycle"
```

### Task 2: Implement The ZLM Preview Relay Manager

**Files:**
- Create: `backend-lite/preview_relay.py`
- Test: `backend-lite/tests/test_preview_relay.py`

- [ ] **Step 1: Implement typed errors and the ZLM API client**

Implement:

```python
class PreviewRelayError(RuntimeError):
    pass


class PreviewRelayTimeout(PreviewRelayError):
    pass


class ZlmPreviewClient:
    def start(self, stream_name: str, source_url: str) -> str:
        params = {
            "secret": self.secret,
            "src_url": source_url,
            "dst_url": f"{self.preview_rtmp_base}/{preview_stream_name(stream_name)}",
            "timeout_ms": str(self.timeout_ms),
            "enable_hls": "0",
            "enable_mp4": "0",
            "ffmpeg_cmd_key": self.command_key,
        }
        payload = self._request("/index/api/addFFmpegSource", params)
        key = str(payload.get("data", {}).get("key", "")).strip()
        if not key:
            raise PreviewRelayError("ZLMediaKit did not return a preview relay key")
        return key

    def stop(self, key: str) -> None:
        self._request("/index/api/delFFmpegSource", {"secret": self.secret, "key": key})
```

Use `urllib.parse.urlencode` for query construction and an injected opener for tests. `_request()` must parse JSON, treat `code != 0` as an error, convert timeout-like failures to `PreviewRelayTimeout`, and expose only a fixed sanitized message.

- [ ] **Step 2: Implement relay naming and lifecycle state**

```python
def preview_stream_name(stream_name: str) -> str:
    return f"preview-{stream_name}"


@dataclass
class RelayState:
    ready: threading.Event
    key: str | None = None
    error: PreviewRelayError | None = None
    viewers: int = 0
    idle_timer: threading.Timer | None = None
    stopping: bool = False
```

Implement `PreviewRelayManager.acquire()`, `release()`, `stop_stream()`, `shutdown()`, and `viewer_count()`. Protect the state dictionary with a lock. Hold the lock while deciding ownership, but do not hold it during HTTP calls. Mark a stream as starting with a per-stream `threading.Event`; concurrent acquisitions wait for the owner and reuse its result instead of starting a second process.

- [ ] **Step 3: Implement idle cleanup safely**

When viewers reach zero, create a daemon timer for `idle_seconds`. On reacquire, cancel and clear it. The timer callback marks the state as stopping under the lock, calls ZLM outside the lock, then removes that exact state and signals waiters. An acquisition that finds a stopping state waits for its completion before creating a replacement, preventing two FFmpeg processes from publishing the same destination. `stop_stream()` and `shutdown()` follow the same state transition and swallow only cleanup errors after logging a credential-free message.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run:

```powershell
rtk python -m pytest -c backend-lite/pytest.ini backend-lite/tests/test_preview_relay.py -q
```

Expected: all relay-manager tests pass.

- [ ] **Step 5: Commit the implementation**

```powershell
rtk git add backend-lite/preview_relay.py backend-lite/tests/test_preview_relay.py
rtk git commit -m "feat: manage ZLM H264 preview relays on demand"
```

### Task 3: Integrate The Existing Live Preview Route

**Files:**
- Create: `backend-lite/tests/test_live_preview_route.py`
- Modify: `backend-lite/main.py`
- Modify: `backend-lite/Dockerfile`
- Test: `backend-lite/tests/test_live_preview_route.py`

- [ ] **Step 1: Write failing route tests**

Build one `CameraResponse` fixture in the global camera store and replace `preview_relay_manager` plus `open_remote` with fakes. Verify:

```python
response = main.proxy_flv_stream("camera-1")
assert fake_manager.acquired == [("camera-1", camera.sourceUrl)]
assert opened_urls == ["http://zlm:82/live/preview-camera-1.live.flv"]
assert asyncio.run(collect_async_body(response.body_iterator)) == b"FLV\x01payload"
assert fake_manager.released == ["camera-1"]
```

Add separate tests that unknown streams return `404`, stopped cameras return `409`, non-RTSP cameras return `400`, relay errors return `502`, relay timeouts return `504`, and an upstream-open failure releases the acquired relay.

- [ ] **Step 2: Run the route tests and verify RED**

Run:

```powershell
rtk python -m pytest -c backend-lite/pytest.ini backend-lite/tests/test_live_preview_route.py -q
```

Expected: failures show that the route still opens the raw ZLM stream and never acquires a preview relay.

- [ ] **Step 3: Configure and instantiate the manager**

Add environment-backed settings in `main.py`:

```python
PREVIEW_IDLE_SECONDS = float(os.getenv("VIDEOAI_PREVIEW_IDLE_SECONDS", "60"))
PREVIEW_START_TIMEOUT_MS = int(os.getenv("VIDEOAI_PREVIEW_START_TIMEOUT_MS", "15000"))
PREVIEW_FFMPEG_CMD_KEY = os.getenv(
    "VIDEOAI_PREVIEW_FFMPEG_CMD_KEY", "ffmpeg.cmd_preview_h264"
).strip()
ZLM_PREVIEW_RTMP_BASE = os.getenv(
    "VIDEOAI_ZLM_PREVIEW_RTMP_BASE", "rtmp://127.0.0.1/live"
).rstrip("/")
```

Construct one `ZlmPreviewClient` and `PreviewRelayManager` after the camera store globals are initialized.

- [ ] **Step 4: Integrate route validation and lifecycle hooks**

Add `require_preview_camera(stream_name)` to find a unique camera and validate `RUNNING` plus `rtsp://`. Change `proxy_flv_stream()` to acquire the derived relay before `open_remote()`, release on upstream-open failure, and release in the response generator's `finally` block.

Call `preview_relay_manager.stop_stream(camera.streamName)` from `stop_camera()` and `delete_camera()`. Call `preview_relay_manager.shutdown()` from the application shutdown handler. Do not change `add_zlmediakit_proxy`, raw stream restoration, worker URLs, frontend API paths, or camera records.

- [ ] **Step 5: Copy the module into the image**

Add this line beside the existing backend source copies:

```dockerfile
COPY preview_relay.py .
```

- [ ] **Step 6: Run route and manager tests and verify GREEN**

Run:

```powershell
rtk python -m pytest -c backend-lite/pytest.ini backend-lite/tests/test_preview_relay.py backend-lite/tests/test_live_preview_route.py -q
```

Expected: all tests pass with no warnings caused by the new code.

- [ ] **Step 7: Commit the integration**

```powershell
rtk git add backend-lite/main.py backend-lite/Dockerfile backend-lite/tests/test_live_preview_route.py
rtk git commit -m "feat: serve live previews through on-demand H264 relays"
```

### Task 4: Add Deployment Configuration And Documentation

**Files:**
- Modify: `.env.example`
- Modify: `docker-compose.yml`
- Modify: `docs/remote-deployment.md`
- Create: `backend-lite/tests/test_deployment_config.py`

- [ ] **Step 1: Write a failing deployment contract test**

Create a backend deployment contract test that reads the root Compose and environment example files, then assert:

```python
assert "VIDEOAI_PREVIEW_IDLE_SECONDS:" in compose
assert "VIDEOAI_PREVIEW_START_TIMEOUT_MS:" in compose
assert "VIDEOAI_PREVIEW_FFMPEG_CMD_KEY:" in compose
assert "VIDEOAI_ZLM_PREVIEW_RTMP_BASE:" in compose
assert "UVICORN_WORKERS: ${UVICORN_WORKERS:-1}" in compose
assert "VIDEOAI_PREVIEW_IDLE_SECONDS=60" in env_example
assert "VIDEOAI_PREVIEW_FFMPEG_CMD_KEY=ffmpeg.cmd_preview_h264" in env_example
```

- [ ] **Step 2: Run the deployment contract test and verify RED**

Run:

```powershell
rtk python -m pytest -c backend-lite/pytest.ini backend-lite/tests/test_deployment_config.py -q
```

Expected: it fails because the preview settings are absent.

- [ ] **Step 3: Add Compose and environment settings**

Add to the backend environment:

```yaml
VIDEOAI_PREVIEW_IDLE_SECONDS: ${VIDEOAI_PREVIEW_IDLE_SECONDS:-60}
VIDEOAI_PREVIEW_START_TIMEOUT_MS: ${VIDEOAI_PREVIEW_START_TIMEOUT_MS:-15000}
VIDEOAI_PREVIEW_FFMPEG_CMD_KEY: ${VIDEOAI_PREVIEW_FFMPEG_CMD_KEY:-ffmpeg.cmd_preview_h264}
VIDEOAI_ZLM_PREVIEW_RTMP_BASE: ${ZLM_PREVIEW_RTMP_BASE:-rtmp://127.0.0.1/live}
UVICORN_WORKERS: ${UVICORN_WORKERS:-1}
```

Add matching non-secret defaults to `.env.example`. Do not add camera usernames, passwords, or the ZLM API secret.

- [ ] **Step 4: Document the ZLM command and checks**

In `docs/remote-deployment.md`, record the exact `[ffmpeg]` entry, the single-worker requirement, the 60-second lifecycle, the `listFFmpegSource`/`getMediaList` checks, an `ffprobe` codec check, and cleanup verification. State that the raw stream remains separate from `preview-{streamName}`.

- [ ] **Step 5: Run the deployment contract test and verify GREEN**

Run:

```powershell
rtk python -m pytest -c backend-lite/pytest.ini backend-lite/tests/test_deployment_config.py -q
rtk docker compose config --quiet
```

Expected: both commands succeed.

- [ ] **Step 6: Commit deployment configuration**

```powershell
rtk git add .env.example docker-compose.yml docs/remote-deployment.md backend-lite/tests/test_deployment_config.py
rtk git commit -m "docs: configure on-demand H264 preview deployment"
```

### Task 5: Verify Locally Before Deployment

**Files:**
- No source changes expected.

- [ ] **Step 1: Run all backend relay tests**

```powershell
rtk python -m pytest -c backend-lite/pytest.ini backend-lite/tests -q
```

Expected: all backend-lite tests pass.

- [ ] **Step 2: Run all frontend contract tests and build**

```powershell
rtk node --test frontend/tests/*.test.mjs
rtk npm --prefix frontend run build
```

Expected: all Node tests pass and Vite creates the production bundle.

- [ ] **Step 3: Validate Compose and inspect the diff**

```powershell
rtk docker compose config --quiet
rtk git diff --check
rtk git status --short
```

Expected: Compose validation and whitespace checks pass; status contains only intended work plus pre-existing user changes.

### Task 6: Configure ZLM And Deploy The Backend

**Files:**
- Modify remote: `/data/cloud-edge-platform/midware/zlmmediakit/config.ini`
- Deploy repository files under remote: `/home/public/videoai`

- [ ] **Step 1: Verify exact remote targets and current values**

Read the ZLM container mount, Compose working directory, current `[ffmpeg]` section, backend environment, and container health. Confirm the config target resolves exactly to `/data/cloud-edge-platform/midware/zlmmediakit/config.ini` before modifying it.

- [ ] **Step 2: Add the idempotent preview command**

Under the existing remote `[ffmpeg]` section, add exactly one entry:

```ini
cmd_preview_h264=%s -rtsp_transport tcp -i %s -an -c:v libx264 -preset ultrafast -tune zerolatency -pix_fmt yuv420p -g 50 -keyint_min 50 -sc_threshold 0 -f flv %s
```

Preserve `bin`, `cmd`, `log`, `restart_sec`, `snap`, and all unrelated sections. Verify there is only one `cmd_preview_h264` key afterward.

- [ ] **Step 3: Deploy only intended repository files**

Transfer `backend-lite/main.py`, `backend-lite/preview_relay.py`, `backend-lite/Dockerfile`, `docker-compose.yml`, and the updated deployment documentation to `/home/public/videoai`, preserving the remote `.env` and camera data.

- [ ] **Step 4: Recreate ZLM and rebuild the backend**

Restart `zlmmediakit_main_1` from `/data/cloud-edge-platform/midware/zlmmediakit`, then rebuild and recreate only `videoai-backend-1` from `/home/public/videoai`. Do not recreate Postgres, worker, Triton, MCP, or frontend.

- [ ] **Step 5: Verify service health before opening a camera**

Check backend `/api/health`, ZLM `/index/api/version`, and confirm `listFFmpegSource` has no unexpected preview sources before testing.

### Task 7: Controlled End-To-End Verification

**Files:**
- No source changes expected unless verification exposes a reproducible defect; any defect must start a new RED/GREEN cycle.

- [ ] **Step 1: Request one known camera preview**

Use the first visible camera stream and hold one `/api/live/{stream}.live.flv` request open. Confirm ZLM `listFFmpegSource` contains exactly one matching `preview-{stream}` source and the host has one corresponding FFmpeg process.

- [ ] **Step 2: Confirm the output codec**

Run `ffprobe` against `http://10.10.3.100:82/live/preview-{stream}.live.flv` with a bounded timeout. Expected video codec: `h264`; no audio stream is required.

- [ ] **Step 3: Confirm relay sharing**

Open a second request for the same camera. Confirm ZLM still lists one FFmpeg source for that derived stream and both requests receive FLV bytes.

- [ ] **Step 4: Confirm browser playback**

Open `http://10.10.3.100:5173/live`, verify the first visible tiles reach non-zero video dimensions, and capture browser console/network evidence showing no FLV codec or reconnect loop errors.

- [ ] **Step 5: Confirm idle cleanup**

Close both requests and the browser page. After 60 seconds plus a small scheduling margin, confirm the preview FFmpeg source, derived media stream, and FFmpeg process are gone.

- [ ] **Step 6: Check resource impact and regressions**

Record host CPU before, during, and after one transcode; verify raw ZLM streams and worker services remain healthy. Confirm no camera credentials appear in backend errors or newly emitted logs.

- [ ] **Step 7: Final verification summary**

Report the tested camera, output codec, relay-sharing result, cleanup timing, browser result, CPU impact, changed containers, and any residual concurrency limit from the single-worker design.
