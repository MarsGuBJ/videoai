package com.videoai.monitoring.api;

import org.springframework.core.io.Resource;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

/**
 * Stored-file download API contract. Implemented by a controller in
 * monitoring-core; not proxied via Feign (streaming resource download).
 */
public interface FileApi {

    @GetMapping("/api/files")
    ResponseEntity<Resource> read(@RequestParam String path);
}
