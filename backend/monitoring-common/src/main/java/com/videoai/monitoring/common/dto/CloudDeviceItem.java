package com.videoai.monitoring.common.dto;

import java.util.UUID;

/**
 * One device entry returned by a cloud platform, enriched with the local diff
 * status during precheck. {@code status}: "new" (云端有本地无) or "update"
 * (同 IP 本地已存在).
 */
public record CloudDeviceItem(
        String name,
        String area,
        String protocol,
        String ip,
        String port,
        String sourceUrl,
        String status,
        UUID localCameraId
) {
}
