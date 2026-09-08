package com.videoai.monitoring.common.vo;

/**
 * Sync result counters after importing selected cloud devices.
 */
public record CloudSyncResultResponse(
        int created,
        int updated,
        int skipped
) {
}
