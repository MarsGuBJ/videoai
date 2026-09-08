package com.videoai.monitoring.core.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;
import java.util.UUID;

/** Row of the {@code gb28181_access_configs} table (V10). */
@Data
@TableName("gb28181_access_configs")
public class Gb28181AccessConfigEntity {
    @TableId(type = IdType.INPUT)
    private UUID id;
    private Boolean enabled;
    private String sipId;
    private String sipDomain;
    private String sipIp;
    private String sipPort;
    private String password;
    private String parentPort;
    private String receivePortStart;
    private String receivePortEnd;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
}
