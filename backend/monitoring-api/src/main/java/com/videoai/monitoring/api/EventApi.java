package com.videoai.monitoring.api;

import com.videoai.monitoring.common.dto.FaceEventIngestRequest;
import com.videoai.monitoring.common.vo.FaceEventResponse;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;
import java.util.UUID;

/**
 * Face event API contract. Implemented by a controller in monitoring-core and
 * proxied via Feign in monitoring-api-rpc (the SSE stream method excluded).
 */
@RequestMapping("/api/events")
public interface EventApi {

    @GetMapping
    List<FaceEventResponse> list(
            @RequestParam(required = false) UUID cameraId,
            @RequestParam(required = false) UUID profileId,
            @RequestParam(defaultValue = "100") int limit
    );

    @GetMapping("/stream")
    SseEmitter stream();

    @PostMapping("/ingest")
    FaceEventResponse ingest(@Valid @RequestBody FaceEventIngestRequest request);
}
