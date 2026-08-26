package com.videoai.monitoring.api;

import com.videoai.monitoring.common.dto.CloudPlatformCreateRequest;
import com.videoai.monitoring.common.dto.CloudPlatformUpdateRequest;
import com.videoai.monitoring.common.vo.CloudPlatformResponse;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;

import java.util.List;
import java.util.UUID;

/**
 * Cloud platform configuration API contract. Implemented by a controller in
 * monitoring-core and proxied via Feign in monitoring-api-rpc.
 */
@RequestMapping("/api/cloud-platforms")
public interface CloudPlatformApi {

    @GetMapping
    List<CloudPlatformResponse> list();

    @PostMapping
    CloudPlatformResponse create(@Valid @RequestBody CloudPlatformCreateRequest request);

    @GetMapping("/{id}")
    CloudPlatformResponse get(@PathVariable UUID id);

    @PatchMapping("/{id}")
    CloudPlatformResponse update(@PathVariable UUID id, @Valid @RequestBody CloudPlatformUpdateRequest request);

    @DeleteMapping("/{id}")
    void delete(@PathVariable UUID id);
}
