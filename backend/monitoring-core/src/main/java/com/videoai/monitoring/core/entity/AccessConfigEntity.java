package com.videoai.monitoring.core.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.Data;

import java.time.OffsetDateTime;

/**
 * Row of the {@code access_config} table (V4). The {@code config} JSONB column
 * is mapped as a raw {@link JsonNode}; the service layer still serializes the
 * concrete config records (Gb28181Config/Ga1400Config) itself.
 */
@Data
@TableName(value = "access_config", autoResultMap = true)
public class AccessConfigEntity {
    @TableId(type = IdType.INPUT)
    private String protocol;
    @TableField(typeHandler = JacksonTypeHandler.class)
    private JsonNode config;
    private OffsetDateTime updatedAt;
}
