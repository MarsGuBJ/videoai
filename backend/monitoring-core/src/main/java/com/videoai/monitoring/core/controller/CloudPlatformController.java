package com.videoai.monitoring.core.controller;

import com.videoai.monitoring.api.CloudPlatformApi;
import com.videoai.monitoring.common.dto.CloudPlatformCreateRequest;
import com.videoai.monitoring.common.dto.CloudPlatformUpdateRequest;
import com.videoai.monitoring.common.dto.CloudSyncRequest;
import com.videoai.monitoring.common.vo.CloudPlatformResponse;
import com.videoai.monitoring.common.vo.CloudSyncPrecheckResponse;
import com.videoai.monitoring.common.vo.CloudSyncResultResponse;
import com.videoai.monitoring.core.service.CloudPlatformService;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

@RestController
public class CloudPlatformController implements CloudPlatformApi {
    private final CloudPlatformService cloudPlatformService;

    public CloudPlatformController(CloudPlatformService cloudPlatformService) {
        this.cloudPlatformService = cloudPlatformService;
    }

    @Override
    public List<CloudPlatformResponse> list() {
        return cloudPlatformService.list();
    }

    @Override
    public CloudPlatformResponse create(CloudPlatformCreateRequest request) {
        return cloudPlatformService.create(request);
    }

    @Override
    public CloudPlatformResponse get(UUID id) {
        return cloudPlatformService.get(id);
    }

    @Override
    public CloudPlatformResponse update(UUID id, CloudPlatformUpdateRequest request) {
        return cloudPlatformService.update(id, request);
    }

    @Override
    public void delete(UUID id) {
        cloudPlatformService.delete(id);
    }

    @Override
    public CloudSyncPrecheckResponse precheck(UUID id) {
        return cloudPlatformService.precheck(id);
    }

    @Override
    public CloudSyncResultResponse sync(UUID id, CloudSyncRequest request) {
        return cloudPlatformService.sync(id, request);
    }
}
