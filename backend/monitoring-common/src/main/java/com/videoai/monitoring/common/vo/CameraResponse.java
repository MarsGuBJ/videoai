package com.videoai.monitoring.common.vo;

import java.time.OffsetDateTime;
import java.util.UUID;

public record CameraResponse(
        UUID id,
        String name,
        String sourceUrl,
        String streamApp,
        String streamName,
        String ffmpegKey,
        String description,
        String area,
        String status,
        String playbackUrl,
        OffsetDateTime createdAt,
        OffsetDateTime updatedAt,
        String nvrId,
        String nvrChannel,
        String nvrTrackId,
        String nvrStreamType,
        String protocol,
        String vendor,
        String ip,
        String port,
        String username,
        String password,
        String deviceCode,
        String serialNumber,
        boolean objectDetectionEnabled
) {
}
