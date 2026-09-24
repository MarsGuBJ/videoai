package com.videoai.monitoring.core.controller;

import com.videoai.monitoring.api.SpatialRegionApi;
import com.videoai.monitoring.common.dto.SpatialConfigUpdateRequest;
import com.videoai.monitoring.common.vo.SpatialConfigResponse;
import com.videoai.monitoring.common.vo.SpatialRegionSyncResponse;
import com.videoai.monitoring.core.service.SpatialConfigService;
import com.videoai.monitoring.core.service.SpatialRegionSyncService;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class SpatialRegionSyncController implements SpatialRegionApi {

    private final SpatialRegionSyncService spatialRegionSyncService;
    private final SpatialConfigService spatialConfigService;

    public SpatialRegionSyncController(SpatialRegionSyncService spatialRegionSyncService,
                                       SpatialConfigService spatialConfigService) {
        this.spatialRegionSyncService = spatialRegionSyncService;
        this.spatialConfigService = spatialConfigService;
    }

    @Override
    public SpatialConfigResponse getSpatialConfig() {
        return spatialConfigService.get();
    }

    @Override
    public SpatialConfigResponse saveSpatialConfig(SpatialConfigUpdateRequest request) {
        return spatialConfigService.save(request);
    }

    @Override
    public SpatialRegionSyncResponse syncSpatial() {
        return spatialRegionSyncService.sync();
    }
}
