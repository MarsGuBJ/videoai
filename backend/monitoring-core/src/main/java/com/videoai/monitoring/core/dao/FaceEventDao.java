package com.videoai.monitoring.core.dao;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.videoai.monitoring.core.entity.FaceEventEntity;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.UUID;

public interface FaceEventDao extends BaseMapper<FaceEventEntity> {

    List<FaceEventEntity> selectFiltered(@Param("cameraId") UUID cameraId,
                                         @Param("profileId") UUID profileId,
                                         @Param("limit") int limit);

    int countRecent(@Param("cameraId") UUID cameraId,
                    @Param("profileId") UUID profileId,
                    @Param("cooldownSeconds") long cooldownSeconds);
}
