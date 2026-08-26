package com.videoai.monitoring.core.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;
import java.util.UUID;

/**
 * Row of the {@code cloud_platforms} table (V5__cloud_platforms).
 */
@Data
@TableName("cloud_platforms")
public class CloudPlatformEntity {
    @TableId(type = IdType.INPUT)
    private UUID id;
    private String name;
    private String type;
    private String key;
    private String secret;
    private String ip;
    private String port;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
}
