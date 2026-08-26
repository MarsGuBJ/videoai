package com.videoai.monitoring.api;

import com.videoai.monitoring.common.dto.CameraCreateRequest;
import com.videoai.monitoring.common.dto.CameraUpdateRequest;
import com.videoai.monitoring.common.dto.PtzControlRequest;
import com.videoai.monitoring.common.vo.CameraResponse;
import com.videoai.monitoring.common.vo.PtzControlResponse;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Camera management API contract. Implemented by a controller in
 * monitoring-core and proxied via Feign in monitoring-api-rpc.
 */
@RequestMapping("/api/cameras")
public interface CameraApi {

    @GetMapping
    List<CameraResponse> list();

    @PostMapping
    CameraResponse create(@Valid @RequestBody CameraCreateRequest request);

    @GetMapping("/{id}")
    CameraResponse get(@PathVariable UUID id);

    @PatchMapping("/{id}")
    CameraResponse update(@PathVariable UUID id, @Valid @RequestBody CameraUpdateRequest request);

    @DeleteMapping("/{id}")
    void delete(@PathVariable UUID id);

    @PostMapping("/{id}/start")
    CameraResponse start(@PathVariable UUID id);

    @PostMapping("/{id}/stop")
    CameraResponse stop(@PathVariable UUID id);

    @PostMapping("/{id}/ptz")
    PtzControlResponse ptz(@PathVariable UUID id, @Valid @RequestBody PtzControlRequest request);

    @GetMapping("/media")
    Map<String, Object> mediaList();
}
