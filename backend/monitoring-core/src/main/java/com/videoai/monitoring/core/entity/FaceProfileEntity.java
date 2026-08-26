package com.videoai.monitoring.core.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;
import java.util.UUID;

/** Row of the {@code face_profiles} table. The embedding stays a TEXT vector literal. */
@Data
@TableName("face_profiles")
public class FaceProfileEntity {
    @TableId(type = IdType.INPUT)
    private UUID id;
    private String name;
    private String description;
    private String photoPath;
    private String embedding;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
}
