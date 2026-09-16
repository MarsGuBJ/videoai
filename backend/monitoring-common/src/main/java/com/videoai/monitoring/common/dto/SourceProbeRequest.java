package com.videoai.monitoring.common.dto;

import jakarta.validation.constraints.NotBlank;

public record SourceProbeRequest(
        @NotBlank String sourceUrl
) {
}
