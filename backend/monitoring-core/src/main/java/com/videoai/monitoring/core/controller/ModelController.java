package com.videoai.monitoring.core.controller;

import com.videoai.monitoring.api.ModelApi;
import com.videoai.monitoring.common.dto.ModelRegisterRequest;
import com.videoai.monitoring.common.vo.ModelConfigResponse;
import com.videoai.monitoring.common.vo.ModelResponse;
import com.videoai.monitoring.core.service.ModelRegistryService;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
public class ModelController implements ModelApi {
    private final ModelRegistryService modelRegistryService;

    public ModelController(ModelRegistryService modelRegistryService) {
        this.modelRegistryService = modelRegistryService;
    }

    @Override
    public List<ModelResponse> list() {
        return modelRegistryService.list();
    }

    @Override
    public ModelResponse register(ModelRegisterRequest request) {
        return modelRegistryService.register(request);
    }

    @Override
    public ModelConfigResponse config(String name) {
        return modelRegistryService.config(name);
    }

    @Override
    public ModelResponse load(String name) {
        return modelRegistryService.load(name);
    }

    @Override
    public ModelResponse unload(String name) {
        return modelRegistryService.unload(name);
    }
}
