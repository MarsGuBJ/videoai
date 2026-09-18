package com.videoai.monitoring.common.vo;

import java.time.OffsetDateTime;
import java.util.UUID;

/** 对外开放的设备变更订阅。 */
public record OpenSubscriptionResponse(
        UUID subscriptionId,
        String name,
        String callbackUrl,
        OffsetDateTime createdAt
) {
}
