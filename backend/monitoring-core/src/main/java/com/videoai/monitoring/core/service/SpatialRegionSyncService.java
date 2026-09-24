package com.videoai.monitoring.core.service;

import com.videoai.monitoring.common.vo.SpatialRegionSyncResponse;

/**
 * 从空间服务同步区域树：只新增缺失节点，已存在的同级同名节点一律复用、不更新。
 */
public interface SpatialRegionSyncService {

    SpatialRegionSyncResponse sync();
}
