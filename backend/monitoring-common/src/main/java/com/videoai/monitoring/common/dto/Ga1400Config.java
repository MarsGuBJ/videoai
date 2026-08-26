package com.videoai.monitoring.common.dto;

/**
 * GA/T 1400 access configuration. Used as the PUT request body for saving the
 * ga1400 config and also embedded in {@code AccessConfigResponse}.
 */
public record Ga1400Config(
        boolean enabled,
        String platformId,
        String platformIp,
        String port,
        String password,
        String resourcePath,
        boolean autoRegister
) {
}
