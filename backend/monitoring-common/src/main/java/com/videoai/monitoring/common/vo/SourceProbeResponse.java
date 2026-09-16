package com.videoai.monitoring.common.vo;

/**
 * 拉流地址探测结果：reachable=false 表示设备不可达（其余字段为 null）；
 * ptzSupported 为 null 表示未判定。
 */
public record SourceProbeResponse(
        boolean reachable,
        String serialNumber,
        Boolean ptzSupported,
        String ip,
        Integer port,
        String username,
        String password
) {
}
