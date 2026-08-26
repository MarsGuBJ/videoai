package com.videoai.monitoring.common.enums;

/**
 * Camera run status. The fixed value set used across the codebase is
 * {@code RUNNING}/{@code STOPPED} (compared as string literals in the stream
 * guard and media stream code, default {@code STOPPED} on import).
 *
 * <p>Note: {@code CameraResponse.status} intentionally remains a {@code String}
 * to keep the JSON wire format identical; this enum is for internal use when
 * comparing or setting status values.
 */
public enum CameraStatus {
    RUNNING,
    STOPPED
}
