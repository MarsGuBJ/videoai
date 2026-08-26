package com.videoai.monitoring.api;

import com.videoai.monitoring.common.vo.HealthResponse;
import org.springframework.web.bind.annotation.GetMapping;

/**
 * Health check API contract. Implemented by a controller in monitoring-core
 * and proxied via Feign in monitoring-api-rpc.
 */
public interface HealthApi {

    @GetMapping("/api/health")
    HealthResponse health();
}
