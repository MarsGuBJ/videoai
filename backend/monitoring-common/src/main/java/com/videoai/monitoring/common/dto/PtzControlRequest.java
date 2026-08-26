package com.videoai.monitoring.common.dto;

import jakarta.validation.constraints.NotBlank;

public record PtzControlRequest(
        @NotBlank String command,
        Integer step,
        Integer preset
) {
}
