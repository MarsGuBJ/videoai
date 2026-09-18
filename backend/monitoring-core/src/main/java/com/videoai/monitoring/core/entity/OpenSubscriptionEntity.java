package com.videoai.monitoring.core.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;
import java.util.UUID;

/** Row of the {@code open_subscriptions} table (V19__open_subscriptions). */
@Data
@TableName("open_subscriptions")
public class OpenSubscriptionEntity {
    @TableId(type = IdType.INPUT)
    private UUID id;
    private String name;
    private String callbackUrl;
    private OffsetDateTime createdAt;
}
