package com.videoai.monitoring.core.dao;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.videoai.monitoring.core.entity.CloudPlatformEntity;

import java.util.List;

public interface CloudPlatformDao extends BaseMapper<CloudPlatformEntity> {

    List<CloudPlatformEntity> selectAllOrdered();

    /** Full update matching the legacy UPDATE statement (sets updated_at = now()). */
    int updateCloudPlatform(CloudPlatformEntity entity);
}
