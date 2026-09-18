package com.videoai.monitoring.common.dto;

import jakarta.validation.constraints.NotBlank;

/** 注册设备变更订阅的请求。 */
public record OpenSubscriptionRequest(
        String name,
        @NotBlank String callbackUrl
) {
}
