package com.videoai.monitoring.common.dto;

import java.util.UUID;

public record WorkerStartRequest(
        UUID cameraId,
        String cameraName,
        String streamUrl
) {
}
