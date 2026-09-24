package com.videoai.monitoring.core.service;

import com.videoai.monitoring.common.dto.SpatialConfigUpdateRequest;
import com.videoai.monitoring.common.vo.SpatialConfigResponse;

/**
 * 空间服务配置读写：基址可在设备管理页区域管理里修改，落库 spatial_config（单行）。
 */
public interface SpatialConfigService {

    SpatialConfigResponse get();

    SpatialConfigResponse save(SpatialConfigUpdateRequest request);

    /**
     * 同步区域树时使用的基址：取库中配置，缺失/为空时回退 application.yml 的
     * {@code videoai.spatial-info.base-url}。返回值不带结尾斜杠。
     */
    String resolveBaseUrl();
}
