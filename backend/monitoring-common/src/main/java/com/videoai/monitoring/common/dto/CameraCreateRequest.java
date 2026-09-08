package com.videoai.monitoring.common.dto;

import jakarta.validation.constraints.NotBlank;

public record CameraCreateRequest(
        @NotBlank String name,
        @NotBlank String sourceUrl,
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
        String serialNumber,
        Boolean videoPreviewEnabled,
        Boolean audioEnabled,
        Boolean talkbackEnabled,
        Boolean ptzEnabled,
        Boolean smartAnalysisEnabled,
        Boolean alarmIoEnabled
) {
}
