package com.videoai.monitoring.common.dto;

/**
 * GB/T 28181 access configuration. Used as the PUT request body for saving the
 * gb28181 config and also embedded in {@code AccessConfigResponse}.
 */
public record Gb28181Config(
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
