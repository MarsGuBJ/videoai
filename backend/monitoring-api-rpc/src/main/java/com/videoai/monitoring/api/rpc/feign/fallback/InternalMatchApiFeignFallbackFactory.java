package com.videoai.monitoring.api.rpc.feign.fallback;

import com.videoai.monitoring.api.rpc.feign.InternalMatchApiFeign;
import com.videoai.monitoring.common.dto.MatchRequest;
import com.videoai.monitoring.common.vo.MatchResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.openfeign.FallbackFactory;
import org.springframework.stereotype.Component;

@Slf4j
@Component
public class InternalMatchApiFeignFallbackFactory implements FallbackFactory<InternalMatchApiFeign> {
    @Override
    public InternalMatchApiFeign create(Throwable cause) {
        log.error("InternalMatchApi feign call failed, fallback triggered", cause);
        return new InternalMatchApiFeign() {
            @Override
            public MatchResponse match(MatchRequest request) {
                return null;
            }
        };
    }
}
