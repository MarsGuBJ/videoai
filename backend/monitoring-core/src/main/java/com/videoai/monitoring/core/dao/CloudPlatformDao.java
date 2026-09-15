package com.videoai.monitoring.core.dao;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.videoai.monitoring.core.entity.CloudPlatformEntity;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface CloudPlatformDao extends BaseMapper<CloudPlatformEntity> {

    List<CloudPlatformEntity> selectAllOrdered();

    List<CloudPlatformEntity> selectByName(@Param("name") String name);

    List<CloudPlatformEntity> selectByKey(@Param("key") String key);

    /** Full update matching the legacy UPDATE statement (sets updated_at = now()). */
    int updateCloudPlatform(CloudPlatformEntity entity);
}
