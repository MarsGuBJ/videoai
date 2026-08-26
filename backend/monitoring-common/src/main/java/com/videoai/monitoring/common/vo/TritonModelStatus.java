package com.videoai.monitoring.common.vo;

public record TritonModelStatus(
        String name,
        String version,
        String state,
        String reason
) {
}
