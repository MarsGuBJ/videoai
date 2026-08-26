package com.videoai.monitoring.common.vo;

import java.time.OffsetDateTime;
import java.util.UUID;

public record FaceEventResponse(
        UUID id,
        UUID cameraId,
        UUID faceProfileId,
        String cameraName,
        String profileName,
        String profileDescription,
        String facePhotoUrl,
        String snapshotUrl,
        OffsetDateTime videoTime,
        double similarity,
        OffsetDateTime createdAt
) {
}
