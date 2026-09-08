package com.videoai.monitoring.common.vo;

import java.time.OffsetDateTime;
import java.util.UUID;

public record Gb28181EntryResponse(
        UUID id,
        boolean enabled,
        String sipId,
        String sipDomain,
        String sipIp,
        String sipPort,
        String password,
        String parentPort,
        String receivePortStart,
        String receivePortEnd,
        OffsetDateTime createdAt,
        OffsetDateTime updatedAt
) {
}
