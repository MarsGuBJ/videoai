package com.videoai.monitoring.common.vo;

import java.time.OffsetDateTime;
import java.util.UUID;

public record Gb28181EntryResponse(
        UUID id,
        String name,
        String sipId,
        String sipIp,
        String sipPort,
        String username,
        String password,
        OffsetDateTime createdAt,
        OffsetDateTime updatedAt,
        String onlineStatus,
        OffsetDateTime lastCheckAt
) {
}
