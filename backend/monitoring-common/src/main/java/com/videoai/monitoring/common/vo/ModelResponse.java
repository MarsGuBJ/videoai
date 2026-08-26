package com.videoai.monitoring.common.vo;

import java.time.OffsetDateTime;
import java.util.UUID;

public record ModelResponse(
        UUID id,
        String name,
        String displayName,
        String repositoryPath,
        String modelType,
        String description,
        String state,
        OffsetDateTime createdAt,
        OffsetDateTime updatedAt
) {
}
