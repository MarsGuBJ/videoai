package com.videoai.monitoring.common.vo;

import java.time.OffsetDateTime;
import java.util.UUID;

public record FaceProfileResponse(
        UUID id,
        String name,
        String description,
        String photoUrl,
        OffsetDateTime createdAt,
        OffsetDateTime updatedAt
) {
}
