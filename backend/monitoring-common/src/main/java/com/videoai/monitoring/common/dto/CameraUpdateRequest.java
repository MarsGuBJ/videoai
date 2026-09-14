package com.videoai.monitoring.common.dto;

import jakarta.validation.constraints.Pattern;

public record CameraUpdateRequest(
        String name,
        String sourceUrl,
        String description,
        String area,
        String nvrId,
        @Pattern(regexp = "^(25[0-6]|2[0-4]\\d|1\\d\\d|[1-9]\\d?)$", message = "必须为1-256的整数") String nvrChannel,
        String nvrTrackId,
        String nvrStreamType,
        String protocol,
        String vendor,
        @Pattern(regexp = "^((25[0-5]|2[0-4]\\d|1\\d\\d|[1-9]?\\d)\\.){3}(25[0-5]|2[0-4]\\d|1\\d\\d|[1-9]?\\d)$", message = "格式不正确") String ip,
        @Pattern(regexp = "^([1-9]\\d{0,3}|[1-5]\\d{4}|6[0-4]\\d{3}|65[0-4]\\d{2}|655[0-2]\\d|6553[0-5])$", message = "必须为1-65535的整数") String port,
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
