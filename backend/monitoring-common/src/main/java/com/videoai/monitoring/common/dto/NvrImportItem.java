package com.videoai.monitoring.common.dto;

/**
 * 从 NVR/CVR 导入的一个摄像头通道条目。
 * sourceUrl 内嵌 NVR 凭据（与设备表现有存储约定一致），仅用于预检查展示与同步提交，不落日志。
 */
public record NvrImportItem(
        String name,
        String ip,
        String port,
        String channel,
        String trackId,
        String nvrHost,
        String sourceUrl,
        String protocol,
        String status,
        String localCameraId
) {
}
