package com.videoai.monitoring.api;

import com.videoai.monitoring.dto.ModelDtos.ModelConfigResponse;
import com.videoai.monitoring.dto.ModelDtos.ModelRegisterRequest;
import com.videoai.monitoring.dto.ModelDtos.ModelResponse;
import com.videoai.monitoring.service.ModelRegistryService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/models")
public class ModelController {
    private final ModelRegistryService modelRegistryService;

    public ModelController(ModelRegistryService modelRegistryService) {
        this.modelRegistryService = modelRegistryService;
    }

    @GetMapping
    List<ModelResponse> list() {
        return modelRegistryService.list();
    }

    @PostMapping("/register")
    ModelResponse register(@Valid @RequestBody ModelRegisterRequest request) {
        return modelRegistryService.register(request);
    }

    @GetMapping("/{name}/config")
    ModelConfigResponse config(@PathVariable String name) {
        return modelRegistryService.config(name);
    }

    @PostMapping("/{name}/load")
    ModelResponse load(@PathVariable String name) {
        return modelRegistryService.load(name);
    }

    @PostMapping("/{name}/unload")
    ModelResponse unload(@PathVariable String name) {
        return modelRegistryService.unload(name);
    }
}

