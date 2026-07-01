package com.videoai.monitoring.dto;

import jakarta.validation.constraints.NotBlank;

import java.time.OffsetDateTime;
import java.util.Map;
import java.util.UUID;

public final class ModelDtos {
    private ModelDtos() {
    }

    public record ModelResponse(
            UUID id,
            String name,
            String displayName,
            String repositoryPath,
            String modelType,
            String description,
            String state,
            OffsetDateTime createdAt,
            OffsetDateTime updatedAt
    ) {
    }

    public record ModelRegisterRequest(
            @NotBlank String name,
            @NotBlank String displayName,
            String repositoryPath,
            @NotBlank String modelType,
            String description
    ) {
    }

    public record TritonModelStatus(
            String name,
            String version,
            String state,
            String reason
    ) {
    }

    public record ModelConfigResponse(
            String name,
            Map<String, Object> config
    ) {
    }
}

