package com.videoai.monitoring.common.vo;

import java.time.OffsetDateTime;
import java.util.UUID;

public record CertificateResponse(
        UUID id,
        String deviceCode,
        String certificate,
        String authMode,
        OffsetDateTime createdAt,
        OffsetDateTime updatedAt
) {
}
