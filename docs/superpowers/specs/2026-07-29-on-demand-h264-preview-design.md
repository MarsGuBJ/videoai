# On-Demand H.264 Live Preview Design

## Goal

Make every browser live-preview request playable when a camera publishes H.265 by having ZLMediaKit start an H.264 FFmpeg relay only while that preview is being watched.

## Current State

- The browser requests `/api/live/{streamName}.live.flv` and plays the response with `flv.js`.
- The backend currently proxies `/live/{streamName}.live.flv` from ZLMediaKit without changing the codec.
- The affected camera main and sub streams are H.265, while `flv.js` requires H.264 video in FLV.
- The remote host runs `zlmediakit/zlmediakit:master`. Its `addFFmpegSource`, `delFFmpegSource`, and `listFFmpegSource` APIs are available, and its bundled FFmpeg provides `libx264`.
- Raw camera proxies must remain available for existing worker and algorithm consumers.

## Selected Approach

The backend will orchestrate a separate preview-only ZLMediaKit FFmpeg source. The public browser URL remains `/api/live/{streamName}.live.flv`; internally, the backend proxies a derived ZLM stream named `preview-{streamName}`.

The first viewer for a camera calls ZLMediaKit `addFFmpegSource` with the camera RTSP URL as `src_url` and `rtmp://127.0.0.1/live/preview-{streamName}` as `dst_url`. ZLMediaKit forks its bundled FFmpeg using a dedicated low-latency H.264 command template. Concurrent viewers share the same relay. After the final viewer disconnects, the backend keeps the relay warm for 60 seconds, then calls `delFFmpegSource`.

## Components

### ZLMediaKit Configuration

Add a dedicated FFmpeg command entry under `[ffmpeg]` without replacing the existing default command:

```ini
cmd_preview_h264=%s -rtsp_transport tcp -i %s -an -c:v libx264 -preset ultrafast -tune zerolatency -pix_fmt yuv420p -g 50 -keyint_min 50 -sc_threshold 0 -f flv %s
```

The backend passes `ffmpeg_cmd_key=ffmpeg.cmd_preview_h264`. Audio is omitted because live preview does not expose audio controls and PCM camera audio would add unnecessary transcoding cost. The derived stream uses H.264/YUV420P for browser compatibility and a bounded keyframe interval for faster startup.

### Backend Preview Relay Manager

Introduce a focused relay manager responsible for:

- Resolving a requested `streamName` to a configured running RTSP camera.
- Building the derived stream name without exposing camera credentials.
- Calling `addFFmpegSource` and retaining the returned source key.
- Waiting until the derived FLV stream is registered before returning it to the proxy route.
- Reference-counting viewers so one camera has at most one preview transcode.
- Cancelling a pending shutdown when a viewer reconnects.
- Calling `delFFmpegSource` after 60 seconds with no viewers.
- Cleaning up managed FFmpeg sources during backend shutdown.

The manager is process-local. Deployment must keep `UVICORN_WORKERS=1`, matching the current remote deployment, so viewer counts and relay ownership remain consistent.

### Existing Live Proxy Route

`GET /api/live/{streamName}.live.flv` keeps its external contract. Before opening the upstream response, it acquires the H.264 preview relay and then proxies `/live/preview-{streamName}.live.flv` from ZLMediaKit. Its generator `finally` block releases the viewer reference even when the browser disconnects abruptly.

The frontend and camera records require no URL changes. Existing raw streams retain their original names and behavior.

## Request Flow

1. The browser opens `/api/live/{streamName}.live.flv`.
2. The backend validates that the stream belongs to a running RTSP camera.
3. The relay manager reuses an existing preview relay or calls `addFFmpegSource`.
4. ZLMediaKit forks FFmpeg, pulls the camera RTSP stream, encodes H.264, and publishes `live/preview-{streamName}`.
5. The backend waits for the derived stream, then forwards its HTTP-FLV bytes to the browser.
6. The browser disconnects; the backend decrements the viewer count.
7. If no viewer reconnects within 60 seconds, the backend deletes the FFmpeg source.

## Concurrency And Lifecycle

- A lock protects relay creation, viewer counts, source keys, and idle deadlines.
- Simultaneous first requests create only one ZLM FFmpeg source.
- A failed startup removes the provisional state so a later request can retry.
- A reconnect during the 60-second grace period reuses the warm relay.
- Stopping or deleting a camera immediately stops its derived preview relay.
- Existing startup restoration and proxy guarding continue to manage raw streams only; they do not prestart preview transcodes.

## Error Handling

- Unknown, stopped, or non-RTSP streams return an explicit HTTP error before contacting ZLM.
- ZLM API failures return `502` without including the camera URL or credentials.
- Preview registration timeout returns `504` and deletes the failed FFmpeg source.
- An upstream FLV connection failure releases the viewer reference and returns a media-service error.
- ZLM response bodies are sanitized in logs so RTSP credentials are not exposed.

## Testing

Automated backend tests will verify:

- The first viewer starts one `addFFmpegSource` relay with the preview command key.
- Multiple viewers reuse one relay.
- The proxy route reads from `preview-{streamName}`, while its public URL is unchanged.
- Viewer disconnect schedules cleanup and reconnect cancels it.
- Idle expiry and camera stop/delete call `delFFmpegSource` exactly once.
- Unknown, stopped, non-RTSP, startup-failure, and timeout paths return the intended errors.
- Existing raw proxy startup and worker stream behavior do not regress.

Deployment verification will use one controlled camera first, inspect ZLM media and FFmpeg source lists, confirm the FLV video codec is H.264 with `ffprobe`, and load the live-preview page in the browser. It will then verify relay reuse and removal after the idle timeout before rebuilding and restarting only the affected backend and ZLMediaKit services.

## Operational Limits

Transcoding is CPU-intensive. The design prevents all configured cameras from being transcoded at startup, but each simultaneously watched camera still consumes one `libx264` process. Monitoring must include FFmpeg process count and host CPU during the controlled rollout. The change does not add GPU encoding because the currently available GPU resources are already occupied by inference workloads.
