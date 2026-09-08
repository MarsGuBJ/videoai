package com.videoai.monitoring.core.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;
import java.util.UUID;

/**
 * Row of the {@code cameras} table (V1__init + V2__camera_nvr_metadata +
 * V3__camera_media_fields).
 */
@Data
@TableName("cameras")
public class CameraEntity {
    @TableId(type = IdType.INPUT)
    private UUID id;
    private String name;
    private String sourceUrl;
    private String streamApp;
    private String streamName;
    private String ffmpegKey;
    private String description;
    private String area;
    private String status;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
    private String nvrId;
    private String nvrChannel;
    private String nvrTrackId;
    private String nvrStreamType;
    private String protocol;
    private String vendor;
    private String ip;
    private String port;
    private String username;
    private String password;
    private String deviceCode;
    private String serialNumber;
    private Boolean videoPreviewEnabled;
    private Boolean audioEnabled;
    private Boolean talkbackEnabled;
    private Boolean ptzEnabled;
    private Boolean smartAnalysisEnabled;
    private Boolean alarmIoEnabled;
}
