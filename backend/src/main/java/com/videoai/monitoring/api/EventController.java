package com.videoai.monitoring.api;

import com.videoai.monitoring.dto.EventDtos.FaceEventIngestRequest;
import com.videoai.monitoring.dto.EventDtos.FaceEventResponse;
import com.videoai.monitoring.service.EventStreamService;
import com.videoai.monitoring.service.FaceEventService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/events")
public class EventController {
    private final FaceEventService faceEventService;
    private final EventStreamService eventStreamService;

    public EventController(FaceEventService faceEventService, EventStreamService eventStreamService) {
        this.faceEventService = faceEventService;
        this.eventStreamService = eventStreamService;
    }

    @GetMapping
    List<FaceEventResponse> list(
            @RequestParam(required = false) UUID cameraId,
            @RequestParam(required = false) UUID profileId,
            @RequestParam(defaultValue = "100") int limit
    ) {
        return faceEventService.list(cameraId, profileId, limit);
    }

    @GetMapping("/stream")
    SseEmitter stream() {
        return eventStreamService.subscribe();
    }

    @PostMapping("/ingest")
    FaceEventResponse ingest(@Valid @RequestBody FaceEventIngestRequest request) {
        return faceEventService.create(request.toCreateRequest(), request.snapshotBase64());
    }
}

