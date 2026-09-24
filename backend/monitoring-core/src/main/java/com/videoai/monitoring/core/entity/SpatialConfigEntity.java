package com.videoai.monitoring.core.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;

/**
 * Row of the {@code spatial_config} table (V20__spatial_config)：单行（id=1）
 * 保存空间服务基址，可在设备管理页区域管理里修改。
 */
@Data
@TableName("spatial_config")
public class SpatialConfigEntity {
    /** 单行配置固定主键。 */
    public static final int SINGLETON_ID = 1;

    @TableId(type = IdType.INPUT)
    private Integer id;
    private String baseUrl;
    private OffsetDateTime updatedAt;
}
