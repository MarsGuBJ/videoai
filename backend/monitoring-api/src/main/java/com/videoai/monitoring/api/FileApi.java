package com.videoai.monitoring.api;

import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.core.io.Resource;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

/**
 * Stored-file download API contract. Implemented by a controller in
 * monitoring-core; not proxied via Feign (streaming resource download).
 */
@Tag(name = "文件")
public interface FileApi {

    @GetMapping("/api/files")
    ResponseEntity<Resource> read(@RequestParam String path);
}
