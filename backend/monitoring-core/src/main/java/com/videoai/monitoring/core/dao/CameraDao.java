package com.videoai.monitoring.core.dao;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.videoai.monitoring.core.entity.CameraEntity;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.UUID;

public interface CameraDao extends BaseMapper<CameraEntity> {

    List<CameraEntity> selectAllOrdered();

    List<CameraEntity> selectByStreamName(@Param("streamName") String streamName);

    /** Full update matching the legacy UPDATE statement (sets updated_at = now()). */
    int updateCamera(CameraEntity entity);

    int updateStatus(@Param("id") UUID id, @Param("status") String status);

    /** Legacy cameras.json import: INSERT ... ON CONFLICT (id) DO NOTHING. */
    int insertIgnore(CameraEntity entity);
}
