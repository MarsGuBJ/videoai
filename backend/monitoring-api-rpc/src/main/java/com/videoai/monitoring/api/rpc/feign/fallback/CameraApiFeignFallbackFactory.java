package com.videoai.monitoring.api.rpc.feign.fallback;

import com.videoai.monitoring.api.rpc.feign.CameraApiFeign;
import com.videoai.monitoring.common.dto.CameraCreateRequest;
import com.videoai.monitoring.common.dto.CameraUpdateRequest;
import com.videoai.monitoring.common.dto.PtzControlRequest;
import com.videoai.monitoring.common.vo.CameraResponse;
import com.videoai.monitoring.common.vo.PtzControlResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.openfeign.FallbackFactory;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@Slf4j
@Component
public class CameraApiFeignFallbackFactory implements FallbackFactory<CameraApiFeign> {
    @Override
    public CameraApiFeign create(Throwable cause) {
        log.error("CameraApi feign call failed, fallback triggered", cause);
        return new CameraApiFeign() {
            @Override
            public List<CameraResponse> list() {
                return List.of();
            }

            @Override
            public CameraResponse create(CameraCreateRequest request) {
                return null;
            }

            @Override
            public CameraResponse get(UUID id) {
                return null;
            }

            @Override
            public CameraResponse update(UUID id, CameraUpdateRequest request) {
                return null;
            }

            @Override
            public void delete(UUID id) {
                // no-op
            }

            @Override
            public CameraResponse start(UUID id) {
                return null;
            }

            @Override
            public CameraResponse stop(UUID id) {
                return null;
            }

            @Override
            public PtzControlResponse ptz(UUID id, PtzControlRequest request) {
                return null;
            }

            @Override
            public Map<String, Object> mediaList() {
                return null;
            }
        };
    }
}
