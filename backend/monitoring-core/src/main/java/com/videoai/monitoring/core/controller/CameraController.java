package com.videoai.monitoring.core.controller;

import com.videoai.monitoring.api.CameraApi;
import com.videoai.monitoring.common.dto.CameraCreateRequest;
import com.videoai.monitoring.common.dto.CameraUpdateRequest;
import com.videoai.monitoring.common.dto.PtzControlRequest;
import com.videoai.monitoring.common.vo.CameraResponse;
import com.videoai.monitoring.common.vo.PtzControlResponse;
import com.videoai.monitoring.core.service.CameraService;
import com.videoai.monitoring.core.service.PtzService;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
public class CameraController implements CameraApi {
    private final CameraService cameraService;
    private final PtzService ptzService;

    public CameraController(CameraService cameraService, PtzService ptzService) {
        this.cameraService = cameraService;
        this.ptzService = ptzService;
    }

    @Override
    public List<CameraResponse> list() {
        return cameraService.list();
    }

    @Override
    public CameraResponse create(CameraCreateRequest request) {
        return cameraService.create(request);
    }

    @Override
    public CameraResponse get(UUID id) {
        return cameraService.get(id);
    }

    @Override
    public CameraResponse update(UUID id, CameraUpdateRequest request) {
        return cameraService.update(id, request);
    }

    @Override
    public void delete(UUID id) {
        cameraService.delete(id);
    }

    @Override
    public CameraResponse start(UUID id) {
        return cameraService.start(id);
    }

    @Override
    public CameraResponse stop(UUID id) {
        return cameraService.stop(id);
    }

    @Override
    public PtzControlResponse ptz(UUID id, PtzControlRequest request) {
        return ptzService.control(id, request);
    }

    @Override
    public Map<String, Object> mediaList() {
        return cameraService.mediaList();
    }
}
