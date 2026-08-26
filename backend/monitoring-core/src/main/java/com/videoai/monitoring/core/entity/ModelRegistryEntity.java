package com.videoai.monitoring.core.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;
import java.util.UUID;

/** Row of the {@code model_registry} table. */
@Data
@TableName("model_registry")
public class ModelRegistryEntity {
    @TableId(type = IdType.INPUT)
    private UUID id;
    private String name;
    private String displayName;
    private String repositoryPath;
    private String modelType;
    private String description;
    private String state;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
}
