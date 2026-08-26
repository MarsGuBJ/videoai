package com.videoai.monitoring.api.rpc.feign;

import com.videoai.monitoring.api.rpc.feign.fallback.FaceProfileApiFeignFallbackFactory;
import com.videoai.monitoring.common.vo.FaceProfileResponse;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;

import java.util.List;
import java.util.UUID;

/**
 * Feign proxy for the face profile API. Does not extend {@code FaceProfileApi}:
 * the multipart {@code create}/{@code update} methods ({@code @RequestPart}
 * with {@code MultipartFile}) are not meaningful over a plain Feign proxy, so
 * only the non-multipart methods are redeclared here.
 */
@FeignClient(value = "monitoring-backend", fallbackFactory = FaceProfileApiFeignFallbackFactory.class)
@RequestMapping("/api/faces")
public interface FaceProfileApiFeign {

    @GetMapping
    List<FaceProfileResponse> list();

    @GetMapping("/{id}")
    FaceProfileResponse get(@PathVariable UUID id);

    @DeleteMapping("/{id}")
    void delete(@PathVariable UUID id);
}
