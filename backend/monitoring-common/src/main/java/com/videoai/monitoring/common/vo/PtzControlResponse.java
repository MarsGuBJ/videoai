package com.videoai.monitoring.common.vo;

import java.util.UUID;

public record PtzControlResponse(
        UUID cameraId,
        String command,
        String channel,
        String targetHost,
        boolean ok
) {
}
