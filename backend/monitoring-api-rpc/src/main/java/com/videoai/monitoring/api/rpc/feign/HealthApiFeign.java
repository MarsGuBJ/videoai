package com.videoai.monitoring.api.rpc.feign;

import com.videoai.monitoring.api.HealthApi;
import com.videoai.monitoring.api.rpc.feign.fallback.HealthApiFeignFallbackFactory;
import org.springframework.cloud.openfeign.FeignClient;

/**
 * Feign proxy for {@link HealthApi}; single plain JSON method, safe to proxy.
 */
@FeignClient(value = "monitoring-backend", fallbackFactory = HealthApiFeignFallbackFactory.class)
public interface HealthApiFeign extends HealthApi {
}
