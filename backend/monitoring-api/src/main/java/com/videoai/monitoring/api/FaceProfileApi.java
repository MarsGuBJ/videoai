package com.videoai.monitoring.api;

import com.videoai.monitoring.common.vo.FaceProfileResponse;
import jakarta.validation.constraints.NotBlank;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.UUID;

/**
 * Face profile API contract (multipart create/update). Implemented by a
 * controller in monitoring-core and proxied via Feign in monitoring-api-rpc
 * (multipart methods excluded there).
 */
@Validated
@RequestMapping("/api/faces")
public interface FaceProfileApi {

    @GetMapping
    List<FaceProfileResponse> list();

    @GetMapping("/{id}")
    FaceProfileResponse get(@PathVariable UUID id);

    @PostMapping
    FaceProfileResponse create(
            @RequestPart("name") @NotBlank String name,
            @RequestPart(value = "description", required = false) String description,
            @RequestPart("photo") MultipartFile photo
    );

    @PatchMapping("/{id}")
    FaceProfileResponse update(
            @PathVariable UUID id,
            @RequestPart("name") @NotBlank String name,
            @RequestPart(value = "description", required = false) String description,
            @RequestPart(value = "photo", required = false) MultipartFile photo
    );

    @DeleteMapping("/{id}")
    void delete(@PathVariable UUID id);
}
