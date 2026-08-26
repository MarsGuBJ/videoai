package com.videoai.monitoring.common.dto;

import jakarta.validation.constraints.NotBlank;

public record CloudPlatformUpdateRequest(
        @NotBlank String name,
        @NotBlank String type,
        @NotBlank String key,
        @NotBlank String secret,
        @NotBlank String ip,
        @NotBlank String port
) {
}
