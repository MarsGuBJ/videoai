package com.videoai.monitoring.core.dao;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.videoai.monitoring.core.entity.Ga1400AccessConfigEntity;

import java.util.List;

public interface Ga1400AccessConfigDao extends BaseMapper<Ga1400AccessConfigEntity> {

    List<Ga1400AccessConfigEntity> selectAllOrdered();
}
