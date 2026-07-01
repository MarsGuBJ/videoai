package com.videoai.monitoring.dto;

import jakarta.validation.constraints.NotBlank;

import java.time.OffsetDateTime;
import java.util.UUID;

public final class CameraDtos {
    private CameraDtos() {
    }

    public record CameraResponse(
            UUID id,
            String name,
            String sourceUrl,
            String streamApp,
            String streamName,
            String ffmpegKey,
            String description,
            String status,
            String playbackUrl,
            OffsetDateTime createdAt,
            OffsetDateTime updatedAt,
            String nvrId,
            String nvrChannel,
            String nvrTrackId,
            String nvrStreamType
    ) {
    }

    public record CameraCreateRequest(
            @NotBlank String name,
            @NotBlank String sourceUrl,
            String description,
            String nvrId,
            String nvrChannel,
            String nvrTrackId,
            String nvrStreamType
    ) {
    }

    public record CameraUpdateRequest(
            @NotBlank String name,
            @NotBlank String sourceUrl,
            String description,
            String nvrId,
            String nvrChannel,
            String nvrTrackId,
            String nvrStreamType
    ) {
    }
}
