package com.videoai.monitoring.api.rpc.feign.fallback;

import com.videoai.monitoring.api.rpc.feign.EventApiFeign;
import com.videoai.monitoring.common.dto.FaceEventIngestRequest;
import com.videoai.monitoring.common.vo.FaceEventResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.openfeign.FallbackFactory;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.UUID;

@Slf4j
@Component
public class EventApiFeignFallbackFactory implements FallbackFactory<EventApiFeign> {
    @Override
    public EventApiFeign create(Throwable cause) {
        log.error("EventApi feign call failed, fallback triggered", cause);
        return new EventApiFeign() {
            @Override
            public List<FaceEventResponse> list(UUID cameraId, UUID profileId, int limit) {
                return List.of();
            }

            @Override
            public FaceEventResponse ingest(FaceEventIngestRequest request) {
                return null;
            }
        };
    }
}
