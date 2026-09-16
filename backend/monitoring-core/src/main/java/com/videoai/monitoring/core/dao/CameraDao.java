package com.videoai.monitoring.core.dao;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.videoai.monitoring.core.entity.CameraEntity;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Map;
import java.util.UUID;

public interface CameraDao extends BaseMapper<CameraEntity> {

    List<CameraEntity> selectAllOrdered();

    List<CameraEntity> selectByStreamName(@Param("streamName") String streamName);

    /** Full update matching the legacy UPDATE statement (sets updated_at = now()). */
    int updateCamera(CameraEntity entity);

    int updateStatus(@Param("id") UUID id, @Param("status") String status);

    /** Legacy cameras.json import: INSERT ... ON CONFLICT (id) DO NOTHING. */
    int insertIgnore(CameraEntity entity);

    /** Rewrite the area path prefix for cameras at or below oldPath (used when a region is renamed). */
    int replaceAreaPrefix(@Param("oldPath") String oldPath, @Param("newPath") String newPath);

    /** Count cameras whose area equals path or sits below it (path / ...). */
    int countByAreaPrefix(@Param("path") String path);

    /** All distinct non-empty camera area path strings. */
    List<String> selectDistinctAreas();

    /** Per-area-path camera counts: rows of {area, cnt}. */
    List<Map<String, Object>> selectAreaCounts();

    /** Existing CAM%05d-style device codes (used to allocate the next auto-generated code). */
    List<String> selectCamDeviceCodes();
}
