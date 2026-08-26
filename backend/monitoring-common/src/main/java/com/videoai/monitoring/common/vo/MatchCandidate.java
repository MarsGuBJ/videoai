package com.videoai.monitoring.common.vo;

import java.util.UUID;

public record MatchCandidate(
        UUID id,
        String name,
        String description,
        String photoPath,
        double similarity
) {
}
