package com.videoai.monitoring.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.time.OffsetDateTime;
import java.util.UUID;

public final class EventDtos {
    private EventDtos() {
    }

    public record FaceEventResponse(
            UUID id,
            UUID cameraId,
            UUID faceProfileId,
            String cameraName,
            String profileName,
            String profileDescription,
            String facePhotoUrl,
            String snapshotUrl,
            OffsetDateTime videoTime,
            double similarity,
            OffsetDateTime createdAt
    ) {
    }

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
}
