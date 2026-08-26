package com.videoai.monitoring.api.rpc.feign;

import com.videoai.monitoring.api.rpc.feign.fallback.MediaStreamApiFeignFallbackFactory;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;

import java.io.IOException;

/**
 * Feign proxy for the media stream API. Does not extend {@code MediaStreamApi}:
 * the FLV/HLS-segment/MJPEG/annotated endpoints return
 * {@code StreamingResponseBody} and cannot be proxied by Feign. Only the HLS
 * playlist endpoint (a plain {@code ResponseEntity<String>}) is redeclared
 * here; note the original controller forwards the raw query string via
 * {@code HttpServletRequest}, which is dropped in this RPC contract.
 */
@FeignClient(value = "monitoring-backend", fallbackFactory = MediaStreamApiFeignFallbackFactory.class)
public interface MediaStreamApiFeign {

    @GetMapping("/api/streams/{streamApp}/{playlistName}.m3u8")
    ResponseEntity<String> proxyHlsPlaylist(@PathVariable String streamApp,
                                            @PathVariable String playlistName) throws IOException;
}
