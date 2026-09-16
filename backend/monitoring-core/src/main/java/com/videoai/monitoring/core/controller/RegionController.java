package com.videoai.monitoring.core.controller;

import com.videoai.monitoring.api.RegionApi;
import com.videoai.monitoring.common.dto.RegionCreateRequest;
import com.videoai.monitoring.common.dto.RegionReorderRequest;
import com.videoai.monitoring.common.dto.RegionUpdateRequest;
import com.videoai.monitoring.common.vo.RegionNodeResponse;
import com.videoai.monitoring.core.service.RegionService;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

@RestController
public class RegionController implements RegionApi {
    private final RegionService regionService;

    public RegionController(RegionService regionService) {
        this.regionService = regionService;
    }

    @Override
    public List<RegionNodeResponse> tree() {
        return regionService.tree();
    }

    @Override
    public RegionNodeResponse create(RegionCreateRequest request) {
        return regionService.create(request);
    }

    @Override
    public RegionNodeResponse rename(UUID id, RegionUpdateRequest request) {
        return regionService.rename(id, request);
    }

    @Override
    public void reorder(RegionReorderRequest request) {
        regionService.reorder(request);
    }

    @Override
    public void delete(UUID id) {
        regionService.delete(id);
    }
}
