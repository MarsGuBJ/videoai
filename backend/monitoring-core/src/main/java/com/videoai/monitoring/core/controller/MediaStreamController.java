package com.videoai.monitoring.core.controller;

import com.videoai.monitoring.api.MediaStreamApi;
import com.videoai.monitoring.common.vo.CameraResponse;
import com.videoai.monitoring.core.config.VideoAiProperties;
import com.videoai.monitoring.core.service.CameraService;
import com.videoai.monitoring.core.service.preview.PreviewRelayException;
import com.videoai.monitoring.core.service.preview.PreviewRelayManager;
import com.videoai.monitoring.core.support.HlsPlaylistRewriter;
import jakarta.servlet.http.HttpServletRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.CacheControl;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Arrays;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

/**
 * Stream distribution endpoints ported from backend-lite/main.py:
 * live FLV preview relay, HLS playlist/segment proxying, MJPEG transcoding and
 * the worker annotated stream.
 */
@RestController
public class MediaStreamController implements MediaStreamApi {
    private static final Logger log = LoggerFactory.getLogger(MediaStreamController.class);
    private static final String MJPEG_CONTENT_TYPE = "multipart/x-mixed-replace; boundary=frame";

    private final CameraService cameraService;
    private final PreviewRelayManager previewRelayManager;
    private final VideoAiProperties properties;
    private final HttpClient httpClient;

    public MediaStreamController(CameraService cameraService, PreviewRelayManager previewRelayManager,
                                 VideoAiProperties properties) {
        this.cameraService = cameraService;
        this.previewRelayManager = previewRelayManager;
        this.properties = properties;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .build();
    }

    @Override
    public ResponseEntity<StreamingResponseBody> proxyFlvStream(String streamName) {
        CameraResponse camera = requirePreviewCamera(streamName);
        String remoteUrl;
        try {
            remoteUrl = previewRelayManager.acquire(streamName, camera.sourceUrl());
        } catch (PreviewRelayException.Timeout exception) {
            throw new ResponseStatusException(HttpStatus.GATEWAY_TIMEOUT, "Preview relay startup timed out", exception);
        } catch (PreviewRelayException exception) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Preview relay startup failed", exception);
        }

        HttpResponse<InputStream> response;
        try {
            response = openPreviewRemote(remoteUrl);
        } catch (Exception exception) {
            previewRelayManager.stopStream(streamName);
            if (exception instanceof ResponseStatusException statusException) {
                throw statusException;
            }
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Preview stream unavailable", exception);
        }

        StreamingResponseBody body = outputStream -> {
            try (InputStream input = response.body()) {
                input.transferTo(outputStream);
            } finally {
                previewRelayManager.release(streamName);
            }
        };
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_TYPE, "video/x-flv")
                .body(body);
    }

    @Override
    public ResponseEntity<String> proxyHlsPlaylist(String streamApp, String playlistName) throws IOException {
        String remoteUrl = srsUrl("/" + streamApp + "/" + playlistName + ".m3u8", currentQueryString());
        byte[] body = fetchRemoteBytes(remoteUrl);
        String rewritten = HlsPlaylistRewriter.rewrite(new String(body, StandardCharsets.UTF_8), streamApp);
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_TYPE, "application/vnd.apple.mpegurl")
                .cacheControl(CacheControl.noStore())
                .body(rewritten);
    }

    @Override
    public ResponseEntity<StreamingResponseBody> proxyHlsSegment(String streamApp, String segmentName) {
        String remoteUrl = srsUrl("/" + streamApp + "/" + segmentName + ".ts", currentQueryString());
        HttpResponse<InputStream> response = openRemote(remoteUrl, Duration.ofSeconds(8));
        StreamingResponseBody body = outputStream -> {
            try (InputStream input = response.body()) {
                input.transferTo(outputStream);
            }
        };
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_TYPE, "video/mp2t")
                .cacheControl(CacheControl.noStore())
                .body(body);
    }

    @Override
    public ResponseEntity<StreamingResponseBody> proxyMjpegStream(String streamApp, String streamName) {
        String sourceUrl = "rtmp://localhost/" + streamApp + "/" + streamName;
        for (CameraResponse camera : cameraService.findByStreamName(streamName)) {
            if (camera.sourceUrl() != null && camera.sourceUrl().startsWith("rtsp://")) {
                sourceUrl = camera.sourceUrl();
                break;
            }
        }
        Process process;
        try {
            process = new ProcessBuilder(
                    properties.ffmpegBin(),
                    "-hide_banner",
                    "-loglevel", "error",
                    "-fflags", "nobuffer",
                    "-flags", "low_delay",
                    "-i", sourceUrl,
                    "-an",
                    "-vf", "fps=8,scale=960:-2",
                    "-q:v", "6",
                    "-f", "mjpeg",
                    "pipe:1")
                    .redirectError(ProcessBuilder.Redirect.DISCARD)
                    .start();
        } catch (IOException exception) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR,
                    "ffmpeg not found: " + properties.ffmpegBin(), exception);
        }

        Process ffmpeg = process;
        StreamingResponseBody body = outputStream -> {
            try (InputStream input = ffmpeg.getInputStream()) {
                byte[] buffer = new byte[0];
                byte[] chunk = new byte[8192];
                int read;
                while ((read = input.read(chunk)) != -1) {
                    byte[] appended = Arrays.copyOf(buffer, buffer.length + read);
                    System.arraycopy(chunk, 0, appended, buffer.length, read);
                    buffer = appended;
                    while (true) {
                        int start = indexOfMarker(buffer, 0, (byte) 0xD8);
                        int end = start >= 0 ? indexOfMarker(buffer, start + 2, (byte) 0xD9) : -1;
                        if (start < 0 || end < 0) {
                            if (start > 0) {
                                buffer = Arrays.copyOfRange(buffer, start, buffer.length);
                            }
                            break;
                        }
                        byte[] frame = Arrays.copyOfRange(buffer, start, end + 2);
                        buffer = Arrays.copyOfRange(buffer, end + 2, buffer.length);
                        outputStream.write(("--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                                + frame.length + "\r\n\r\n").getBytes(StandardCharsets.US_ASCII));
                        outputStream.write(frame);
                        outputStream.write("\r\n".getBytes(StandardCharsets.US_ASCII));
                        outputStream.flush();
                    }
                }
            } finally {
                terminate(ffmpeg);
            }
        };
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_TYPE, MJPEG_CONTENT_TYPE)
                .cacheControl(CacheControl.noStore())
                .body(body);
    }

    @Override
    public ResponseEntity<StreamingResponseBody> annotatedCameraStream(UUID cameraId) {
        CameraResponse camera = cameraService.get(cameraId);
        if (!camera.objectDetectionEnabled()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND,
                    "Object detection stream is not enabled for this camera");
        }
        if (!"RUNNING".equals(camera.status())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Camera is not running");
        }
        String remoteUrl = properties.worker().url()
                + "/v1/streams/annotated.mjpeg?cameraId=" + camera.id();
        HttpResponse<InputStream> response = openRemote(remoteUrl, Duration.ofSeconds(60));
        StreamingResponseBody body = outputStream -> {
            try (InputStream input = response.body()) {
                input.transferTo(outputStream);
            }
        };
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_TYPE, MJPEG_CONTENT_TYPE)
                .body(body);
    }

    /** require_preview_camera from backend-lite/main.py. */
    private CameraResponse requirePreviewCamera(String streamName) {
        List<CameraResponse> matches = cameraService.findByStreamName(streamName);
        if (matches.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Camera stream not found");
        }
        if (matches.size() > 1) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Camera stream name is not unique");
        }
        CameraResponse camera = matches.get(0);
        if (!"RUNNING".equals(camera.status())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Camera is not running");
        }
        if (camera.sourceUrl() == null || !camera.sourceUrl().toLowerCase().startsWith("rtsp://")) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Camera does not provide an RTSP source");
        }
        return camera;
    }

    /** open_preview_remote: retry 404s until the preview start timeout elapses. */
    private HttpResponse<InputStream> openPreviewRemote(String remoteUrl) {
        long timeoutMs = Math.max(1, properties.preview().startTimeoutMs());
        long deadline = System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(timeoutMs);
        while (true) {
            try {
                return openRemote(remoteUrl, Duration.ofSeconds(8));
            } catch (ResponseStatusException exception) {
                if (exception.getStatusCode().value() != 404 || System.nanoTime() >= deadline) {
                    throw exception;
                }
                try {
                    Thread.sleep(250);
                } catch (InterruptedException interrupted) {
                    Thread.currentThread().interrupt();
                    throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Preview stream unavailable", interrupted);
                }
            }
        }
    }

    private byte[] fetchRemoteBytes(String remoteUrl) throws IOException {
        HttpResponse<InputStream> response = openRemote(remoteUrl, Duration.ofSeconds(8));
        try (InputStream input = response.body()) {
            return input.readAllBytes();
        }
    }

    /** open_remote: HTTP errors keep their status code, connection failures map to 502. */
    private HttpResponse<InputStream> openRemote(String url, Duration timeout) {
        HttpRequest request = HttpRequest.newBuilder(URI.create(url))
                .timeout(timeout)
                .header("User-Agent", "VideoAI-Lite/1.0")
                .GET()
                .build();
        HttpResponse<InputStream> response;
        try {
            response = httpClient.send(request, HttpResponse.BodyHandlers.ofInputStream());
        } catch (IOException exception) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY,
                    "SRS stream unavailable: " + exception.getMessage(), exception);
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "SRS stream unavailable", exception);
        }
        if (response.statusCode() >= 400) {
            int status = response.statusCode();
            try {
                response.body().close();
            } catch (IOException ignored) {
                // best effort
            }
            throw new ResponseStatusException(HttpStatus.valueOf(status), "SRS stream request failed");
        }
        return response;
    }

    private String srsUrl(String path, String query) {
        String base = properties.zlm().httpUrl();
        String url = base + (path.startsWith("/") ? path : "/" + path);
        return query != null && !query.isEmpty() ? url + "?" + query : url;
    }

    /**
     * The MediaStreamApi contract drops the HttpServletRequest parameter the
     * legacy controller used to forward the raw query string; recover it from
     * the current request context instead.
     */
    private static String currentQueryString() {
        HttpServletRequest request =
                ((ServletRequestAttributes) RequestContextHolder.currentRequestAttributes()).getRequest();
        return request.getQueryString();
    }

    private void terminate(Process process) {
        if (process.isAlive()) {
            process.destroy();
            try {
                if (!process.waitFor(2, TimeUnit.SECONDS)) {
                    process.destroyForcibly();
                }
            } catch (InterruptedException exception) {
                Thread.currentThread().interrupt();
                process.destroyForcibly();
            }
        }
    }

    private static int indexOfMarker(byte[] data, int from, byte marker) {
        for (int index = Math.max(0, from); index < data.length - 1; index++) {
            if (data[index] == (byte) 0xFF && data[index + 1] == marker) {
                return index;
            }
        }
        return -1;
    }
}
