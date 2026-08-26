package com.videoai.monitoring.api.rpc.feign.fallback;

import com.videoai.monitoring.api.rpc.feign.FaceProfileApiFeign;
import com.videoai.monitoring.common.vo.FaceProfileResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.openfeign.FallbackFactory;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.UUID;

@Slf4j
@Component
public class FaceProfileApiFeignFallbackFactory implements FallbackFactory<FaceProfileApiFeign> {
    @Override
    public FaceProfileApiFeign create(Throwable cause) {
        log.error("FaceProfileApi feign call failed, fallback triggered", cause);
        return new FaceProfileApiFeign() {
            @Override
            public List<FaceProfileResponse> list() {
                return List.of();
            }

            @Override
            public FaceProfileResponse get(UUID id) {
                return null;
            }

            @Override
            public void delete(UUID id) {
                // no-op
            }
        };
    }
}
