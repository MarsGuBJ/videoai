package com.videoai.monitoring.core.client;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

import java.util.List;

/**
 * 空间服务 {@code /spatialServer/spatialInfo/tree} 的响应包装：
 * {@code {status, message, code, data:[...]}}。
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record SpatialInfoTreeResponse(
        boolean status,
        String message,
        String code,
        List<SpatialInfoNode> data
) {
}
