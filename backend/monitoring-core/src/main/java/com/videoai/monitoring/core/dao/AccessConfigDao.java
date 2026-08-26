package com.videoai.monitoring.core.dao;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.videoai.monitoring.core.entity.AccessConfigEntity;
import org.apache.ibatis.annotations.Param;

public interface AccessConfigDao extends BaseMapper<AccessConfigEntity> {

    /** Raw JSON text of the config column, exactly as the legacy JdbcClient read it. */
    String selectConfig(@Param("protocol") String protocol);

    /** Legacy upsert with CAST(:config AS jsonb). */
    int upsertConfig(@Param("protocol") String protocol, @Param("config") String config);
}
