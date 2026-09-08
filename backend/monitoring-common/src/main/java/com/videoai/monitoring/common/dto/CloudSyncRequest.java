package com.videoai.monitoring.common.dto;

import java.util.List;

/**
 * Sync request for a cloud platform: the selected device items from precheck,
 * the target area applied to newly created cameras, and whether cloud data
 * overwrites local cameras with the same IP.
 */
public record CloudSyncRequest(
        List<CloudDeviceItem> items,
        String targetArea,
        Boolean overwrite
) {
}
