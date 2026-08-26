package com.videoai.monitoring.common.dto;

import jakarta.validation.constraints.NotBlank;

public record FaceUpdateRequest(
        @NotBlank String name,
        String description
) {
}
