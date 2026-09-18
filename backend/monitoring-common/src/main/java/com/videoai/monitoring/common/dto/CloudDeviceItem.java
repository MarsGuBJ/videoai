package com.videoai.monitoring.common.dto;

import java.util.UUID;

/**
 * One device entry returned by a cloud platform, enriched with the local diff
 * status during precheck. {@code status}: "new" (云端有本地无) or "update"
 * (同 IP 本地已存在). GB28181 级联来源的设备无 ip/sourceUrl，以 {@code gbCode}
 * （国标 DeviceID）判重入库。
 */
public record CloudDeviceItem(
        String name,
        String area,
        String protocol,
        String ip,
        String port,
        String sourceUrl,
        String status,
        UUID localCameraId,
        String gbCode
) {
}
