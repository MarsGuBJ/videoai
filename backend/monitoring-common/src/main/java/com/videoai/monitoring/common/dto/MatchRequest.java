package com.videoai.monitoring.common.dto;

import jakarta.validation.constraints.NotNull;

public record MatchRequest(@NotNull float[] embedding, Double threshold) {
}
