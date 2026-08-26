package com.videoai.monitoring.api.rpc.feign.fallback;

import com.videoai.monitoring.api.rpc.feign.ModelApiFeign;
import com.videoai.monitoring.common.dto.ModelRegisterRequest;
import com.videoai.monitoring.common.vo.ModelConfigResponse;
import com.videoai.monitoring.common.vo.ModelResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.openfeign.FallbackFactory;
import org.springframework.stereotype.Component;

import java.util.List;

@Slf4j
@Component
public class ModelApiFeignFallbackFactory implements FallbackFactory<ModelApiFeign> {
    @Override
    public ModelApiFeign create(Throwable cause) {
        log.error("ModelApi feign call failed, fallback triggered", cause);
        return new ModelApiFeign() {
            @Override
            public List<ModelResponse> list() {
                return List.of();
            }

            @Override
            public ModelResponse register(ModelRegisterRequest request) {
                return null;
            }

            @Override
            public ModelConfigResponse config(String name) {
                return null;
            }

            @Override
            public ModelResponse load(String name) {
                return null;
            }

            @Override
            public ModelResponse unload(String name) {
                return null;
            }
        };
    }
}
