package com.videoai.monitoring.api;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

import java.io.IOException;
import java.util.UUID;

/**
 * Stream distribution API contract ported from backend-lite/main.py: live FLV
 * preview relay, HLS playlist/segment proxying, MJPEG transcoding and the
 * worker annotated stream. Implemented by a controller in monitoring-core;
 * only the non-streaming methods are proxied via Feign in monitoring-api-rpc.
 *
 * <p>Deviation from the original controller: the {@code HttpServletRequest}
 * parameter of {@code proxyHlsPlaylist}/{@code proxyHlsSegment} (used only to
 * forward the raw query string to SRS) is dropped here because jakarta.servlet
 * is not on the API module's classpath and servlet types do not belong in an
 * RPC-shared contract. Implementations can still obtain the current request via
 * {@code RequestContextHolder} if query forwarding is needed.
 */
public interface MediaStreamApi {

    @GetMapping("/api/live/{streamName}.live.flv")
    ResponseEntity<StreamingResponseBody> proxyFlvStream(@PathVariable String streamName);

    @GetMapping("/api/streams/{streamApp}/{playlistName}.m3u8")
    ResponseEntity<String> proxyHlsPlaylist(@PathVariable String streamApp,
                                            @PathVariable String playlistName) throws IOException;

    @GetMapping("/api/streams/{streamApp}/{segmentName}.ts")
    ResponseEntity<StreamingResponseBody> proxyHlsSegment(@PathVariable String streamApp,
                                                          @PathVariable String segmentName);

    @GetMapping("/api/streams/{streamApp}/{streamName}.mjpeg")
    ResponseEntity<StreamingResponseBody> proxyMjpegStream(@PathVariable String streamApp,
                                                           @PathVariable String streamName);

    @GetMapping("/api/cameras/{cameraId}/annotated.mjpeg")
    ResponseEntity<StreamingResponseBody> annotatedCameraStream(@PathVariable UUID cameraId);
}
