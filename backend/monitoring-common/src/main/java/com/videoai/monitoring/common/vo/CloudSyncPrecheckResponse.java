package com.videoai.monitoring.common.vo;

import com.videoai.monitoring.common.dto.CloudDeviceItem;

import java.util.List;

/**
 * Precheck result: cloud devices diffed against local cameras by IP.
 */
public record CloudSyncPrecheckResponse(
        List<CloudDeviceItem> items,
        int newCount,
        int updateCount
) {
}
