package com.videoai.monitoring.core.service;

import com.videoai.monitoring.common.dto.FaceEventCreateRequest;
import com.videoai.monitoring.common.vo.FaceEventResponse;

import java.util.List;
import java.util.UUID;

public interface FaceEventService {

    List<FaceEventResponse> list(UUID cameraId, UUID profileId, int limit);

    FaceEventResponse create(FaceEventCreateRequest request, String snapshotBase64);

    FaceEventResponse get(UUID id);
}
