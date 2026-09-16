package com.videoai.monitoring.common.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import java.util.UUID;

public record RegionCreateRequest(
        @NotBlank @Pattern(regexp = "^[^/]+$", message = "名称不能包含 /") String name,
        UUID parentId
) {
}
