package com.videoai.monitoring.common.vo;

import java.time.OffsetDateTime;
import java.util.UUID;

public record CloudPlatformResponse(
        UUID id,
        String name,
        String type,
        String key,
        String secret,
        String ip,
        String port,
        OffsetDateTime createdAt,
        OffsetDateTime updatedAt
) {
}
