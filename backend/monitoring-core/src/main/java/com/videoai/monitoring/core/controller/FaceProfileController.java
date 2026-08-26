package com.videoai.monitoring.core.controller;

import com.videoai.monitoring.api.FaceProfileApi;
import com.videoai.monitoring.common.dto.FaceUpdateRequest;
import com.videoai.monitoring.common.vo.FaceProfileResponse;
import com.videoai.monitoring.core.service.FaceProfileService;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.UUID;

@RestController
public class FaceProfileController implements FaceProfileApi {
    private final FaceProfileService faceProfileService;

    public FaceProfileController(FaceProfileService faceProfileService) {
        this.faceProfileService = faceProfileService;
    }

    @Override
    public List<FaceProfileResponse> list() {
        return faceProfileService.list();
    }

    @Override
    public FaceProfileResponse get(UUID id) {
        return faceProfileService.get(id);
    }

    @Override
    public FaceProfileResponse create(String name, String description, MultipartFile photo) {
        return faceProfileService.create(name, description, photo);
    }

    @Override
    public FaceProfileResponse update(UUID id, String name, String description, MultipartFile photo) {
        return faceProfileService.update(id, new FaceUpdateRequest(name, description), photo);
    }

    @Override
    public void delete(UUID id) {
        faceProfileService.delete(id);
    }
}
