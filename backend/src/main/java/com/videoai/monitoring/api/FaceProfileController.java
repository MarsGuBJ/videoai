package com.videoai.monitoring.api;

import com.videoai.monitoring.dto.FaceDtos.FaceProfileResponse;
import com.videoai.monitoring.dto.FaceDtos.FaceUpdateRequest;
import com.videoai.monitoring.service.FaceProfileService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.UUID;

@Validated
@RestController
@RequestMapping("/api/faces")
public class FaceProfileController {
    private final FaceProfileService faceProfileService;

    public FaceProfileController(FaceProfileService faceProfileService) {
        this.faceProfileService = faceProfileService;
    }

    @GetMapping
    List<FaceProfileResponse> list() {
        return faceProfileService.list();
    }

    @GetMapping("/{id}")
    FaceProfileResponse get(@PathVariable UUID id) {
        return faceProfileService.get(id);
    }

    @PostMapping
    FaceProfileResponse create(
            @RequestPart("name") @NotBlank String name,
            @RequestPart(value = "description", required = false) String description,
            @RequestPart("photo") MultipartFile photo
    ) {
        return faceProfileService.create(name, description, photo);
    }

    @PatchMapping("/{id}")
    FaceProfileResponse update(
            @PathVariable UUID id,
            @RequestPart("name") @NotBlank String name,
            @RequestPart(value = "description", required = false) String description,
            @RequestPart(value = "photo", required = false) MultipartFile photo
    ) {
        return faceProfileService.update(id, new FaceUpdateRequest(name, description), photo);
    }

    @DeleteMapping("/{id}")
    void delete(@PathVariable UUID id) {
        faceProfileService.delete(id);
    }
}
