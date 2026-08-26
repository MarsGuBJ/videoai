package com.videoai.monitoring.api.rpc.feign;

import com.videoai.monitoring.api.AccessConfigApi;
import com.videoai.monitoring.api.rpc.feign.fallback.AccessConfigApiFeignFallbackFactory;
import org.springframework.cloud.openfeign.FeignClient;

/**
 * Feign proxy for {@link AccessConfigApi}; all methods are plain JSON
 * request/response and safe to proxy.
 */
@FeignClient(value = "monitoring-backend", fallbackFactory = AccessConfigApiFeignFallbackFactory.class)
public interface AccessConfigApiFeign extends AccessConfigApi {
}
