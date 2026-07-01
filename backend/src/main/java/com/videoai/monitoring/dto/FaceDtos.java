package com.videoai.monitoring.dto;

import jakarta.validation.constraints.NotBlank;

import java.time.OffsetDateTime;
import java.util.UUID;

public final class FaceDtos {
    private FaceDtos() {
    }

    public record FaceProfileResponse(
            UUID id,
            String name,
            String description,
            String photoUrl,
            OffsetDateTime createdAt,
            OffsetDateTime updatedAt
    ) {
    }

    public record FaceUpdateRequest(
            @NotBlank String name,
            String description
    ) {
    }

    public record EmbeddingResponse(float[] embedding) {
    }

    public record MatchCandidate(
            UUID id,
            String name,
            String description,
            String photoPath,
            double similarity
    ) {
    }
}

