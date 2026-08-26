package com.videoai.monitoring.core.dao;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.videoai.monitoring.core.entity.FaceProfileEntity;

import java.util.List;

public interface FaceProfileDao extends BaseMapper<FaceProfileEntity> {

    List<FaceProfileEntity> selectAllOrdered();

    /** Legacy update including photo/embedding replacement (sets updated_at = now()). */
    int updateWithPhoto(FaceProfileEntity entity);

    /** Legacy update without touching photo/embedding (sets updated_at = now()). */
    int updateWithoutPhoto(FaceProfileEntity entity);
}
