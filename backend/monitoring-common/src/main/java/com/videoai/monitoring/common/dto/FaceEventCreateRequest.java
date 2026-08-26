package com.videoai.monitoring.common.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.time.OffsetDateTime;
import java.util.UUID;

public record FaceEventCreateRequest(
        @NotNull UUID cameraId,
        @NotNull UUID faceProfileId,
        @NotBlank String cameraName,
        @NotBlank String profileName,
        String profileDescription,
        @NotBlank String facePhotoPath,
        String snapshotPath,
        @NotNull OffsetDateTime videoTime,
        double similarity
) {
}
