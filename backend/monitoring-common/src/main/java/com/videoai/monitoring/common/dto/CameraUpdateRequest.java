package com.videoai.monitoring.common.dto;

public record CameraUpdateRequest(
        String name,
        String sourceUrl,
        String description,
        String area,
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
        String serialNumber
) {
}
