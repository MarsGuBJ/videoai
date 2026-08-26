package com.videoai.monitoring.common.vo;

import java.util.Map;

public record ModelConfigResponse(
        String name,
        Map<String, Object> config
) {
}
