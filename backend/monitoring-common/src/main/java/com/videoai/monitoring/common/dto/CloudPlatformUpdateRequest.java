package com.videoai.monitoring.common.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

public record CloudPlatformUpdateRequest(
        @NotBlank String name,
        @NotBlank String type,
        @NotBlank String key,
        @NotBlank String secret,
        @NotBlank @Pattern(regexp = "^((25[0-5]|2[0-4]\\d|1\\d\\d|[1-9]?\\d)\\.){3}(25[0-5]|2[0-4]\\d|1\\d\\d|[1-9]?\\d)$", message = "格式不正确") String ip,
        @NotBlank @Pattern(regexp = "^([1-9]\\d{0,3}|[1-5]\\d{4}|6[0-4]\\d{3}|65[0-4]\\d{2}|655[0-2]\\d|6553[0-5])$", message = "必须为1-65535的整数") String port
) {
}
