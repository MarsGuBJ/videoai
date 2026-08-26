package com.videoai.monitoring.api.rpc.feign;

import com.videoai.monitoring.api.rpc.feign.fallback.EventApiFeignFallbackFactory;
import com.videoai.monitoring.common.dto.FaceEventIngestRequest;
import com.videoai.monitoring.common.vo.FaceEventResponse;
import jakarta.validation.Valid;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;

import java.util.List;
import java.util.UUID;

/**
 * Feign proxy for the event API. Does not extend {@code EventApi}: the SSE
 * {@code stream()} method cannot be proxied by Feign, so only the plain
 * request/response methods are redeclared here.
 */
@FeignClient(value = "monitoring-backend", fallbackFactory = EventApiFeignFallbackFactory.class)
@RequestMapping("/api/events")
public interface EventApiFeign {

    @GetMapping
    List<FaceEventResponse> list(
            @RequestParam(required = false) UUID cameraId,
            @RequestParam(required = false) UUID profileId,
            @RequestParam(defaultValue = "100") int limit
    );

    @PostMapping("/ingest")
    FaceEventResponse ingest(@Valid @RequestBody FaceEventIngestRequest request);
}
