package com.videoai.monitoring.common.vo;

import java.time.OffsetDateTime;

/**
 * 空间服务配置：{@code baseUrl} 为同步区域树时调用的空间服务基址。
 */
public record SpatialConfigResponse(
        String baseUrl,
        OffsetDateTime updatedAt
) {
}
