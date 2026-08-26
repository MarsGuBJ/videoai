package com.videoai.monitoring.core.service;

import com.videoai.monitoring.common.dto.ModelRegisterRequest;
import com.videoai.monitoring.common.vo.ModelConfigResponse;
import com.videoai.monitoring.common.vo.ModelResponse;

import java.util.List;

public interface ModelRegistryService {

    List<ModelResponse> list();

    ModelResponse register(ModelRegisterRequest request);

    ModelResponse load(String name);

    ModelResponse unload(String name);

    ModelConfigResponse config(String name);
}
