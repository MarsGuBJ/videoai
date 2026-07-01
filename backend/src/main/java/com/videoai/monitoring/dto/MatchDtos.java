package com.videoai.monitoring.dto;

import jakarta.validation.constraints.NotNull;

public final class MatchDtos {
    private MatchDtos() {
    }

    public record MatchRequest(@NotNull float[] embedding, Double threshold) {
    }

    public record MatchResponse(
            boolean matched,
            java.util.UUID id,
            String name,
            String description,
            String photoPath,
            double similarity
    ) {
    }
}

