package com.videoai.monitoring.common.vo;

import java.util.UUID;

public record MatchResponse(
        boolean matched,
        UUID id,
        String name,
        String description,
        String photoPath,
        double similarity
) {
}
