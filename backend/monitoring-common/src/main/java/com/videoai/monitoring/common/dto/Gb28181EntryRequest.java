package com.videoai.monitoring.common.dto;

/**
 * Upsert request body for a GB/T 28181 access config entry (multi-entry table).
 * Has no id/timestamps; mirrors the field set of {@link Gb28181Config}.
 */
public record Gb28181EntryRequest(
        boolean enabled,
        String sipId,
        String sipDomain,
        String sipIp,
        String sipPort,
        String password,
        String parentPort,
        String receivePortStart,
        String receivePortEnd
) {
}
