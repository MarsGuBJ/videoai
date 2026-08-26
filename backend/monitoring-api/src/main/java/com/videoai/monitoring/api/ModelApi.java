package com.videoai.monitoring.api;

import com.videoai.monitoring.common.dto.ModelRegisterRequest;
import com.videoai.monitoring.common.vo.ModelConfigResponse;
import com.videoai.monitoring.common.vo.ModelResponse;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;

import java.util.List;

/**
 * Model registry API contract. Implemented by a controller in monitoring-core
 * and proxied via Feign in monitoring-api-rpc.
 */
@RequestMapping("/api/models")
public interface ModelApi {

    @GetMapping
    List<ModelResponse> list();

    @PostMapping("/register")
    ModelResponse register(@Valid @RequestBody ModelRegisterRequest request);

    @GetMapping("/{name}/config")
    ModelConfigResponse config(@PathVariable String name);

    @PostMapping("/{name}/load")
    ModelResponse load(@PathVariable String name);

    @PostMapping("/{name}/unload")
    ModelResponse unload(@PathVariable String name);
}
