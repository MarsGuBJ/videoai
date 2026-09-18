package com.videoai.monitoring.common.vo;

import java.time.OffsetDateTime;

/**
 * 推送给订阅方的设备事件消息。
 * DEVICE_DELETED 时 device 只含 deviceId/name，其余字段为 null。
 */
public record DeviceEventMessage(
        String eventType,
        OffsetDateTime timestamp,
        OpenDeviceResponse device
) {
    public static final String SNAPSHOT = "DEVICE_SNAPSHOT";
    public static final String CREATED = "DEVICE_CREATED";
    public static final String UPDATED = "DEVICE_UPDATED";
    public static final String DELETED = "DEVICE_DELETED";
    public static final String STATUS_CHANGED = "DEVICE_STATUS_CHANGED";
}
