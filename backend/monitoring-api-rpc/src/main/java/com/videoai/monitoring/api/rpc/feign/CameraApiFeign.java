package com.videoai.monitoring.api.rpc.feign;

import com.videoai.monitoring.api.CameraApi;
import com.videoai.monitoring.api.rpc.feign.fallback.CameraApiFeignFallbackFactory;
import org.springframework.cloud.openfeign.FeignClient;

/**
 * Feign proxy for {@link CameraApi}; all methods are plain JSON request/response
 * and safe to proxy.
 */
@FeignClient(value = "monitoring-backend", fallbackFactory = CameraApiFeignFallbackFactory.class)
public interface CameraApiFeign extends CameraApi {
}
