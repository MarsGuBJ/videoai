package com.videoai.monitoring.core.service.impl;

import com.videoai.monitoring.common.vo.CameraResponse;
import com.videoai.monitoring.core.client.ZlmClient;
import com.videoai.monitoring.core.service.CameraService;
import com.videoai.monitoring.core.service.LiveRelayService;
import com.videoai.monitoring.core.service.StreamGuardService;
import com.videoai.monitoring.core.support.StreamUrls;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.core.annotation.Order;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Service
@Order(2)
public class StreamGuardServiceImpl implements StreamGuardService {
    private static final Logger log = LoggerFactory.getLogger(StreamGuardServiceImpl.class);

    private final CameraService cameraService;
    private final LiveRelayService liveRelayService;
    private final ZlmClient zlmClient;

    public StreamGuardServiceImpl(CameraService cameraService, LiveRelayService liveRelayService, ZlmClient zlmClient) {
        this.cameraService = cameraService;
        this.liveRelayService = liveRelayService;
        this.zlmClient = zlmClient;
    }

    @Override
    public void run(ApplicationArguments args) {
        restoreRunningCameraStreams();
    }

    @Override
    public void restoreRunningCameraStreams() {
        for (CameraResponse camera : cameraService.list()) {
            if (!"RUNNING".equals(camera.status())) {
                continue;
            }
            try {
                liveRelayService.addZlmediakitProxy(camera.sourceUrl(), camera.streamName());
                addSubStreamProxy(camera);
            } catch (Exception exception) {
                log.warn("restore_running_camera_streams failed for {}: {}", camera.streamName(), exception.getMessage());
            }
        }
    }

    @Override
    @Scheduled(fixedDelay = 30000, initialDelay = 30000)
    public void reconcileStreams() {
        try {
            Set<String> activeStreams = fetchActiveStreams();
            for (CameraResponse camera : cameraService.list()) {
                if (!"RUNNING".equals(camera.status())) {
                    continue;
                }
                if (!activeStreams.contains(camera.streamName())) {
                    log.info("stream_proxy_guard: re-adding proxy for {}", camera.streamName());
                    liveRelayService.addZlmediakitProxy(camera.sourceUrl(), camera.streamName(), true);
                }
                String subStreamName = camera.subStreamName();
                if (subStreamName != null && !activeStreams.contains(subStreamName)) {
                    log.info("stream_proxy_guard: re-adding proxy for {}", subStreamName);
                    liveRelayService.addZlmediakitProxy(
                            StreamUrls.deriveSubSourceUrl(camera.sourceUrl()), subStreamName, true);
                }
            }
        } catch (Exception exception) {
            log.warn("stream_proxy_guard failed: {}", exception.getMessage());
        }
    }

    /** 与主码流对称：可推导子码流地址的 RUNNING 设备同时恢复子码流代理。 */
    private void addSubStreamProxy(CameraResponse camera) {
        String subStreamName = camera.subStreamName();
        String subSourceUrl = StreamUrls.deriveSubSourceUrl(camera.sourceUrl());
        if (subStreamName != null && subSourceUrl != null) {
            liveRelayService.addZlmediakitProxy(subSourceUrl, subStreamName);
        }
    }

    /** _fetch_active_streams from backend-lite/main.py. */
    @SuppressWarnings("unchecked")
    private Set<String> fetchActiveStreams() {
        try {
            Map<String, Object> response = zlmClient.mediaList();
            Object code = response.get("code");
            if (code != null && code.toString().equals("0")) {
                Object data = response.get("data");
                if (data instanceof List<?> items) {
                    Set<String> streams = new HashSet<>();
                    for (Object item : items) {
                        if (item instanceof Map<?, ?> entry && entry.get("stream") != null) {
                            streams.add(entry.get("stream").toString());
                        }
                    }
                    return streams;
                }
            }
        } catch (Exception exception) {
            log.debug("fetch active streams failed: {}", exception.getMessage());
        }
        return Set.of();
    }
}
