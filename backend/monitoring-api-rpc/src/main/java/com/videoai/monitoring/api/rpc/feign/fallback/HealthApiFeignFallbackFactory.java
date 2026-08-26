package com.videoai.monitoring.api.rpc.feign.fallback;

import com.videoai.monitoring.api.rpc.feign.HealthApiFeign;
import com.videoai.monitoring.common.vo.HealthResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.openfeign.FallbackFactory;
import org.springframework.stereotype.Component;

@Slf4j
@Component
public class HealthApiFeignFallbackFactory implements FallbackFactory<HealthApiFeign> {
    @Override
    public HealthApiFeign create(Throwable cause) {
        log.error("HealthApi feign call failed, fallback triggered", cause);
        return new HealthApiFeign() {
            @Override
            public HealthResponse health() {
                return null;
            }
        };
    }
}
