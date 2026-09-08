package com.videoai.monitoring.core.service;

import com.videoai.monitoring.common.dto.CloudPlatformCreateRequest;
import com.videoai.monitoring.common.dto.CloudPlatformUpdateRequest;
import com.videoai.monitoring.common.dto.CloudSyncRequest;
import com.videoai.monitoring.common.vo.CloudPlatformResponse;
import com.videoai.monitoring.common.vo.CloudSyncPrecheckResponse;
import com.videoai.monitoring.common.vo.CloudSyncResultResponse;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Cloud platform configuration CRUD.
 */
public interface CloudPlatformService {

    List<CloudPlatformResponse> list();

    CloudPlatformResponse get(UUID id);

    Optional<CloudPlatformResponse> find(UUID id);

    CloudPlatformResponse create(CloudPlatformCreateRequest request);

    CloudPlatformResponse update(UUID id, CloudPlatformUpdateRequest request);

    void delete(UUID id);

    /** Fetch the platform's device list and diff it against local cameras by IP. */
    CloudSyncPrecheckResponse precheck(UUID id);

    /** Import the selected cloud devices into the local camera list. */
    CloudSyncResultResponse sync(UUID id, CloudSyncRequest request);
}
