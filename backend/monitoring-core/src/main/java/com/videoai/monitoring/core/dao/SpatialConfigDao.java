package com.videoai.monitoring.core.dao;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.videoai.monitoring.core.entity.SpatialConfigEntity;

/**
 * 空间服务配置（单行表 spatial_config）。读写走 BaseMapper 的 selectById / insert / updateById。
 */
public interface SpatialConfigDao extends BaseMapper<SpatialConfigEntity> {
}
