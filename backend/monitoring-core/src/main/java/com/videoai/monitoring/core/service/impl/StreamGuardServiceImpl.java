package com.videoai.monitoring.core.service.impl;

import com.videoai.monitoring.common.vo.CameraResponse;
import com.videoai.monitoring.core.client.ZlmClient;
import com.videoai.monitoring.core.dao.CameraDao;
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
import java.util.concurrent.ConcurrentHashMap;

@Service
@Order(2)
public class StreamGuardServiceImpl implements StreamGuardService {
    private static final Logger log = LoggerFactory.getLogger(StreamGuardServiceImpl.class);
    /**
     * 连续挂流失败次数达到该值、且设备可达（online_status 不是 OFFLINE）时，判定为拉流地址/通道不可用，
     * 把拉流状态降为 STOPPED，避免设备长期显示"拉流中"却没有任何流（假在线）。
     */
    private static final int MAX_ATTACH_FAILURES = 3;

    private final CameraService cameraService;
    private final LiveRelayService liveRelayService;
    private final ZlmClient zlmClient;
    private final CameraDao cameraDao;
    /** streamName -> 连续挂流失败次数（仅内存计数，重启后重新统计）。 */
    private final Map<String, Integer> attachFailures = new ConcurrentHashMap<>();

    public StreamGuardServiceImpl(CameraService cameraService, LiveRelayService liveRelayService,
                                  ZlmClient zlmClient, CameraDao cameraDao) {
        this.cameraService = cameraService;
        this.liveRelayService = liveRelayService;
        this.zlmClient = zlmClient;
        this.cameraDao = cameraDao;
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
                liveRelayService.addZlmediakitProxy(camera.sourceUrl(), camera.streamName(), false, camera.audioEnabled());
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
                    attachFailures.remove(camera.streamName());
                    continue;
                }
                if (activeStreams.contains(camera.streamName())) {
                    attachFailures.remove(camera.streamName());
                } else {
                    log.info("stream_proxy_guard: re-adding proxy for {}", camera.streamName());
                    boolean attached = liveRelayService.addZlmediakitProxy(
                            camera.sourceUrl(), camera.streamName(), true, camera.audioEnabled());
                    recordAttachResult(camera, attached);
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

    /**
     * 挂流失败且设备可达（不是 OFFLINE）：连续失败 {@link #MAX_ATTACH_FAILURES} 次后把拉流状态降为 STOPPED。
     * 设备本身不可达（OFFLINE）时不降级——保留 RUNNING 表示"设备恢复后继续拉流"的意图，
     * 由 {@link CameraStatusScanService} 维护的设备可达性表达离线。
     */
    private void recordAttachResult(CameraResponse camera, boolean attached) {
        if (attached) {
            attachFailures.remove(camera.streamName());
            return;
        }
        int failures = attachFailures.merge(camera.streamName(), 1, Integer::sum);
        if (failures >= MAX_ATTACH_FAILURES && !CameraStatusScanService.OFFLINE.equalsIgnoreCase(camera.onlineStatus())) {
            attachFailures.remove(camera.streamName());
            cameraDao.updateStatus(camera.id(), "STOPPED");
            log.warn("stream_proxy_guard: {} 连续 {} 次挂流失败且设备可达，拉流状态置为 STOPPED（请检查拉流地址/通道）",
                    camera.streamName(), failures);
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
