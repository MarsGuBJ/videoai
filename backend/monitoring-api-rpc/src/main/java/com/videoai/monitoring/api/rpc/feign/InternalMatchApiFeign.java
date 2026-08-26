package com.videoai.monitoring.api.rpc.feign;

import com.videoai.monitoring.api.InternalMatchApi;
import com.videoai.monitoring.api.rpc.feign.fallback.InternalMatchApiFeignFallbackFactory;
import org.springframework.cloud.openfeign.FeignClient;

/**
 * Feign proxy for {@link InternalMatchApi}; single plain JSON method, safe to
 * proxy.
 */
@FeignClient(value = "monitoring-backend", fallbackFactory = InternalMatchApiFeignFallbackFactory.class)
public interface InternalMatchApiFeign extends InternalMatchApi {
}
