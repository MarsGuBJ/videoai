package com.videoai.monitoring.common.dto;

import jakarta.validation.constraints.NotBlank;

/**
 * 保存空间服务基址请求。地址必须是绝对 http/https URL。
 */
public record SpatialConfigUpdateRequest(
        @NotBlank(message = "空间服务地址不能为空") String baseUrl
) {
}
