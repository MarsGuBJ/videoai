package com.videoai.monitoring.common.dto;

import jakarta.validation.constraints.NotNull;

import java.util.List;
import java.util.UUID;

public record RegionReorderRequest(
        UUID parentId,
        @NotNull List<UUID> orderedIds
) {
}
