package com.videoai.monitoring.common.vo;

import java.util.UUID;

/**
 * 对外开放的设备列表项：名称、位置、在线状态、基础信息与固定视频流链接。
 * 不暴露拉流地址、用户名、密码等内部/敏感字段（与 CameraResponse 刻意区分）。
 */
public record OpenDeviceResponse(
        UUID deviceId,
        String name,
        String area,
        String onlineStatus,
        String streamUrl,
        BasicInfo basicInfo
) {
    /** 设备管理中的基础信息（剔除凭据）。 */
    public record BasicInfo(
            String deviceCode,
            String protocol,
            String vendor,
            String ip,
            String port,
            String serialNumber,
            String deviceCategory,
            String deviceType,
            String channelName,
            String gbCode,
            String description,
            String nvrId,
            String nvrChannel,
            String nvrStreamType
    ) {
    }
}
