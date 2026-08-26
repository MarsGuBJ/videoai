package com.videoai.monitoring.api.rpc.feign;

import com.videoai.monitoring.api.rpc.feign.fallback.FileApiFeignFallbackFactory;
import org.springframework.cloud.openfeign.FeignClient;

/**
 * Feign proxy for the file API. Declares no methods: the sole endpoint
 * ({@code GET /api/files}) streams a {@code ResponseEntity<Resource>} file
 * download, which is not meaningful over a Feign proxy. Callers should fetch
 * files directly via HTTP.
 */
@FeignClient(value = "monitoring-backend", fallbackFactory = FileApiFeignFallbackFactory.class)
public interface FileApiFeign {
}
