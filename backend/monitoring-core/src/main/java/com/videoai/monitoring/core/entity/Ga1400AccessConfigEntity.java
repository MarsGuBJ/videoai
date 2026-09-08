package com.videoai.monitoring.core.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;
import java.util.UUID;

/** Row of the {@code ga1400_access_configs} table (V9). */
@Data
@TableName("ga1400_access_configs")
public class Ga1400AccessConfigEntity {
    @TableId(type = IdType.INPUT)
    private UUID id;
    private Boolean enabled;
    private String platformId;
    private String platformIp;
    private String port;
    private String password;
    private String resourcePath;
    private Boolean autoRegister;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
}
