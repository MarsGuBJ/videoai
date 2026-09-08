package com.videoai.monitoring.common.vo;

import java.time.OffsetDateTime;
import java.util.UUID;

public record Ga1400EntryResponse(
        UUID id,
        boolean enabled,
        String platformId,
        String platformIp,
        String port,
        String password,
        String resourcePath,
        boolean autoRegister,
        OffsetDateTime createdAt,
        OffsetDateTime updatedAt
) {
}
