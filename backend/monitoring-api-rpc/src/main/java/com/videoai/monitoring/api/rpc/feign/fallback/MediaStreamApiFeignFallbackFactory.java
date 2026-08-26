package com.videoai.monitoring.api.rpc.feign.fallback;

import com.videoai.monitoring.api.rpc.feign.MediaStreamApiFeign;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.openfeign.FallbackFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;

@Slf4j
@Component
public class MediaStreamApiFeignFallbackFactory implements FallbackFactory<MediaStreamApiFeign> {
    @Override
    public MediaStreamApiFeign create(Throwable cause) {
        log.error("MediaStreamApi feign call failed, fallback triggered", cause);
        return new MediaStreamApiFeign() {
            @Override
            public ResponseEntity<String> proxyHlsPlaylist(String streamApp, String playlistName) {
                return ResponseEntity.notFound().build();
            }
        };
    }
}
