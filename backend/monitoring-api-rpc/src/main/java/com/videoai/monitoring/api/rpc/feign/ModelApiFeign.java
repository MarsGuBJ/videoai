package com.videoai.monitoring.api.rpc.feign;

import com.videoai.monitoring.api.ModelApi;
import com.videoai.monitoring.api.rpc.feign.fallback.ModelApiFeignFallbackFactory;
import org.springframework.cloud.openfeign.FeignClient;

/**
 * Feign proxy for {@link ModelApi}; all methods are plain JSON request/response
 * and safe to proxy.
 */
@FeignClient(value = "monitoring-backend", fallbackFactory = ModelApiFeignFallbackFactory.class)
public interface ModelApiFeign extends ModelApi {
}
