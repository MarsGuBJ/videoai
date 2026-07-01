package com.videoai.monitoring.api;

import com.videoai.monitoring.dto.CameraDtos.CameraCreateRequest;
import com.videoai.monitoring.dto.CameraDtos.CameraResponse;
import com.videoai.monitoring.dto.CameraDtos.CameraUpdateRequest;
import com.videoai.monitoring.service.CameraService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/cameras")
public class CameraController {
    private final CameraService cameraService;

    public CameraController(CameraService cameraService) {
        this.cameraService = cameraService;
    }

    @GetMapping
    List<CameraResponse> list() {
        return cameraService.list();
    }

    @PostMapping
    CameraResponse create(@Valid @RequestBody CameraCreateRequest request) {
        return cameraService.create(request);
    }

    @GetMapping("/{id}")
    CameraResponse get(@PathVariable UUID id) {
        return cameraService.get(id);
    }

    @PatchMapping("/{id}")
    CameraResponse update(@PathVariable UUID id, @Valid @RequestBody CameraUpdateRequest request) {
        return cameraService.update(id, request);
    }

    @DeleteMapping("/{id}")
    void delete(@PathVariable UUID id) {
        cameraService.delete(id);
    }

    @PostMapping("/{id}/start")
    CameraResponse start(@PathVariable UUID id) {
        return cameraService.start(id);
    }

    @PostMapping("/{id}/stop")
    CameraResponse stop(@PathVariable UUID id) {
        return cameraService.stop(id);
    }

    @GetMapping("/media")
    Map<String, Object> mediaList() {
        return cameraService.mediaList();
    }
}

