package com.videoai.monitoring.core.controller;

import com.videoai.monitoring.api.EventApi;
import com.videoai.monitoring.common.dto.FaceEventIngestRequest;
import com.videoai.monitoring.common.vo.FaceEventResponse;
import com.videoai.monitoring.core.service.EventStreamService;
import com.videoai.monitoring.core.service.FaceEventService;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;
import java.util.UUID;

@RestController
public class EventController implements EventApi {
    private final FaceEventService faceEventService;
    private final EventStreamService eventStreamService;

    public EventController(FaceEventService faceEventService, EventStreamService eventStreamService) {
        this.faceEventService = faceEventService;
        this.eventStreamService = eventStreamService;
    }

    @Override
    public List<FaceEventResponse> list(UUID cameraId, UUID profileId, int limit) {
        return faceEventService.list(cameraId, profileId, limit);
    }

    @Override
    public SseEmitter stream() {
        return eventStreamService.subscribe();
    }

    @Override
    public FaceEventResponse ingest(FaceEventIngestRequest request) {
        return faceEventService.create(request.toCreateRequest(), request.snapshotBase64());
    }
}
