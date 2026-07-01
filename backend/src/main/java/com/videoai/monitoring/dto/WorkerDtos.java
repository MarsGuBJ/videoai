package com.videoai.monitoring.dto;

import java.util.Map;
import java.util.UUID;

public final class WorkerDtos {
    private WorkerDtos() {
    }

    public record WorkerStartRequest(
            UUID cameraId,
            String cameraName,
            String streamUrl
    ) {
    }

    public record WorkerStopRequest(UUID cameraId) {
    }

    public record WorkerStatusResponse(Map<String, String> streams) {
    }
}

