package com.videoai.monitoring.core.dao;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.videoai.monitoring.core.entity.Gb28181AccessConfigEntity;

import java.util.List;

public interface Gb28181AccessConfigDao extends BaseMapper<Gb28181AccessConfigEntity> {

    List<Gb28181AccessConfigEntity> selectAllOrdered();
}
