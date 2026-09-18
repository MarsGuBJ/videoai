package com.videoai.monitoring.core.support;

import com.videoai.monitoring.common.vo.CameraResponse;
import com.videoai.monitoring.common.vo.OpenDeviceResponse;

/**
 * CameraResponse -> OpenDeviceResponse 映射，供对外列表接口与订阅推送共用。
 */
public final class OpenDevicePayloads {

    private OpenDevicePayloads() {
    }

    public static OpenDeviceResponse toOpenDevice(CameraResponse camera) {
        String streamUrl = camera.sourceUrl() != null && !camera.sourceUrl().isBlank()
                ? "/api/open/devices/" + camera.id() + "/live.flv"
                : null;
        return new OpenDeviceResponse(
                camera.id(),
                camera.name(),
                camera.area(),
                camera.onlineStatus(),
                streamUrl,
                new OpenDeviceResponse.BasicInfo(
                        camera.deviceCode(),
                        camera.protocol(),
                        camera.vendor(),
                        camera.ip(),
                        camera.port(),
                        camera.serialNumber(),
                        camera.deviceCategory(),
                        camera.deviceType(),
                        camera.channelName(),
                        camera.gbCode(),
                        camera.description(),
                        camera.nvrId(),
                        camera.nvrChannel(),
                        camera.nvrStreamType()
                )
        );
    }

    /** DEVICE_DELETED 载荷：只携带 deviceId/name，其余字段为 null。 */
    public static OpenDeviceResponse deletedDevice(java.util.UUID deviceId, String name) {
        return new OpenDeviceResponse(deviceId, name, null, null, null, null);
    }
}
