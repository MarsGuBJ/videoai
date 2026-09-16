package com.videoai.monitoring.api;

import com.videoai.monitoring.common.dto.RegionCreateRequest;
import com.videoai.monitoring.common.dto.RegionReorderRequest;
import com.videoai.monitoring.common.dto.RegionUpdateRequest;
import com.videoai.monitoring.common.vo.RegionNodeResponse;
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
 * Region tree API contract. Implemented by a controller in monitoring-core.
 */
@RequestMapping("/api/regions")
public interface RegionApi {

    @GetMapping("/tree")
    List<RegionNodeResponse> tree();

    @PostMapping
    RegionNodeResponse create(@Valid @RequestBody RegionCreateRequest request);

    @PatchMapping("/{id}")
    RegionNodeResponse rename(@PathVariable UUID id, @Valid @RequestBody RegionUpdateRequest request);

    @PostMapping("/reorder")
    void reorder(@Valid @RequestBody RegionReorderRequest request);

    @DeleteMapping("/{id}")
    void delete(@PathVariable UUID id);
}
