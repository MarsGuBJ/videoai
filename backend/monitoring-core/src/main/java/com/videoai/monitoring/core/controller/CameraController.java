package com.videoai.monitoring.core.controller;

import com.videoai.monitoring.api.CameraApi;
import com.videoai.monitoring.common.dto.CameraCreateRequest;
import com.videoai.monitoring.common.dto.CameraUpdateRequest;
import com.videoai.monitoring.common.dto.PtzControlRequest;
import com.videoai.monitoring.common.dto.SourceProbeRequest;
import com.videoai.monitoring.common.vo.CameraResponse;
import com.videoai.monitoring.common.vo.PtzControlResponse;
import com.videoai.monitoring.common.vo.SourceProbeResponse;
import com.videoai.monitoring.core.client.DeviceSourceProbe;
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
    /** 无状态工具，直接持有即可 */
    private final DeviceSourceProbe sourceProbe = new DeviceSourceProbe();

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
    public SourceProbeResponse probeSource(SourceProbeRequest request) {
        DeviceSourceProbe.ParsedSource parsed = DeviceSourceProbe.parseSource(request.sourceUrl());
        DeviceSourceProbe.ProbeResult result = sourceProbe.probe(request.sourceUrl());
        return new SourceProbeResponse(
                result.reachable(),
                result.serialNumber(),
                result.ptzSupported(),
                parsed != null ? parsed.host() : null,
                parsed != null ? parsed.port() : null,
                parsed != null ? parsed.username() : null,
                parsed != null ? parsed.password() : null);
    }

    @Override
    public Map<String, Object> mediaList() {
        return cameraService.mediaList();
    }
}
