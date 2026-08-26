package com.videoai.monitoring.core.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;
import java.util.UUID;

/** Row of the {@code face_events} table. */
@Data
@TableName("face_events")
public class FaceEventEntity {
    @TableId(type = IdType.INPUT)
    private UUID id;
    private UUID cameraId;
    private UUID faceProfileId;
    private String cameraName;
    private String profileName;
    private String profileDescription;
    private String facePhotoPath;
    private String snapshotPath;
    private OffsetDateTime videoTime;
    private Double similarity;
    private OffsetDateTime createdAt;
}
