package com.videoai.monitoring.core.dao;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.videoai.monitoring.core.entity.Ga1400AccessConfigEntity;
import org.apache.ibatis.annotations.Param;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

public interface Ga1400AccessConfigDao extends BaseMapper<Ga1400AccessConfigEntity> {

    List<Ga1400AccessConfigEntity> selectAllOrdered();

    /** 在线探测服务专用：只更新状态列，不触碰用户编辑字段与 updated_at。 */
    int updateOnlineStatus(@Param("id") UUID id, @Param("onlineStatus") String onlineStatus,
                           @Param("lastCheckAt") OffsetDateTime lastCheckAt);
}
