package com.videoai.monitoring.common.vo;

import java.util.List;
import java.util.UUID;

public record RegionNodeResponse(
        UUID id,
        String name,
        UUID parentId,
        int sortOrder,
        int deviceCount,
        List<RegionNodeResponse> children
) {
}
