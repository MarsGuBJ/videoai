package com.videoai.monitoring.core.dao;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.videoai.monitoring.core.entity.RegionEntity;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.UUID;

public interface RegionDao extends BaseMapper<RegionEntity> {

    List<RegionEntity> selectAll();

    /** Sibling lookup by name; a null parentId matches root nodes (parent_id IS NULL). */
    List<RegionEntity> selectByParentAndName(@Param("parentId") UUID parentId, @Param("name") String name);

    /** Max sort_order among siblings (null parentId = roots); null when no rows. */
    Integer maxSortOrder(@Param("parentId") UUID parentId);

    /** Update name / sort_order (sets updated_at = now()). */
    int updateRegion(RegionEntity entity);
}
