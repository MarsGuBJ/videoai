package com.videoai.monitoring.core.dao;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.videoai.monitoring.core.entity.ModelRegistryEntity;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.UUID;

public interface ModelRegistryDao extends BaseMapper<ModelRegistryEntity> {

    List<ModelRegistryEntity> selectAllOrdered();

    /** Legacy register upsert: INSERT ... ON CONFLICT (name) DO UPDATE. */
    int upsert(ModelRegistryEntity entity);

    int updateStateById(@Param("id") UUID id, @Param("state") String state);

    int updateStateByName(@Param("name") String name, @Param("state") String state);
}
