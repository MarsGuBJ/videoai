package com.videoai.monitoring.core.service;

import com.videoai.monitoring.common.dto.FaceUpdateRequest;
import com.videoai.monitoring.common.vo.FaceProfileResponse;
import com.videoai.monitoring.common.vo.MatchCandidate;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.UUID;

public interface FaceProfileService {

    List<FaceProfileResponse> list();

    FaceProfileResponse get(UUID id);

    FaceProfileResponse create(String name, String description, MultipartFile photo);

    FaceProfileResponse update(UUID id, FaceUpdateRequest request, MultipartFile photo);

    void delete(UUID id);

    MatchCandidate match(float[] embedding, double threshold);
}
