package com.videoai.monitoring.core.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;
import java.util.UUID;

/**
 * Row of the {@code regions} table (V14__regions).
 */
@Data
@TableName("regions")
public class RegionEntity {
    @TableId(type = IdType.INPUT)
    private UUID id;
    private String name;
    private UUID parentId;
    private Integer sortOrder;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
}
