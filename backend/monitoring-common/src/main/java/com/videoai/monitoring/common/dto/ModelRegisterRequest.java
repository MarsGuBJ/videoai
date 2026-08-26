package com.videoai.monitoring.common.dto;

import jakarta.validation.constraints.NotBlank;

public record ModelRegisterRequest(
        @NotBlank String name,
        @NotBlank String displayName,
        String repositoryPath,
        @NotBlank String modelType,
        String description
) {
}
