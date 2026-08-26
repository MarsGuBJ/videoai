package com.videoai.monitoring.core.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;
import java.util.UUID;

/** Row of the {@code device_certificates} table (V4). */
@Data
@TableName("device_certificates")
public class DeviceCertificateEntity {
    @TableId(type = IdType.INPUT)
    private UUID id;
    private String deviceCode;
    private String certificate;
    private String authMode;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
}
