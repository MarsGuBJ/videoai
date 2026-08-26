package com.videoai.monitoring.common.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.time.OffsetDateTime;
import java.util.UUID;

public record FaceEventIngestRequest(
        @NotNull UUID cameraId,
        @NotNull UUID faceProfileId,
        @NotBlank String cameraName,
        @NotBlank String profileName,
        String profileDescription,
        @NotBlank String facePhotoPath,
        String snapshotBase64,
        @NotNull OffsetDateTime videoTime,
        double similarity
) {
    public FaceEventCreateRequest toCreateRequest() {
        return new FaceEventCreateRequest(
                cameraId,
                faceProfileId,
                cameraName,
                profileName,
                profileDescription,
                facePhotoPath,
                null,
                videoTime,
                similarity
        );
    }
}
