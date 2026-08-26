package com.videoai.monitoring.core.service;

import com.videoai.monitoring.common.dto.CameraCreateRequest;
import com.videoai.monitoring.common.dto.CameraUpdateRequest;
import com.videoai.monitoring.common.vo.CameraResponse;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * Camera CRUD and start/stop semantics ported from backend-lite/main.py.
 * Worker stream reconciliation is intentionally not handled here (the Python side owns it).
 */
public interface CameraService {

    List<CameraResponse> list();

    CameraResponse get(UUID id);

    Optional<CameraResponse> find(UUID id);

    List<CameraResponse> findByStreamName(String streamName);

    CameraResponse create(CameraCreateRequest request);

    CameraResponse update(UUID id, CameraUpdateRequest request);

    void delete(UUID id);

    CameraResponse start(UUID id);

    CameraResponse stop(UUID id);

    Map<String, Object> mediaList();

    /** camera_with_runtime_flags: objectDetectionEnabled is derived from the source host. */
    boolean isDinoCamera(String sourceUrl);
}
