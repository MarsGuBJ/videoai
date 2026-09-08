package com.videoai.monitoring.common.dto;

/**
 * Upsert request body for a GA/T 1400 access config entry (multi-entry table).
 * Has no id/timestamps; mirrors the field set of {@link Ga1400Config}.
 */
public record Ga1400EntryRequest(
        boolean enabled,
        String platformId,
        String platformIp,
        String port,
        String password,
        String resourcePath,
        boolean autoRegister
) {
}
