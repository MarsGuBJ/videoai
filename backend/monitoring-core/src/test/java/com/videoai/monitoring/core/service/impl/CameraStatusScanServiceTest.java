package com.videoai.monitoring.core.service.impl;

import com.videoai.monitoring.core.dao.CameraDao;
import com.videoai.monitoring.core.entity.CameraEntity;
import com.videoai.monitoring.core.service.LiveRelayService;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

class CameraStatusScanServiceTest {

    private final CameraDao cameraDao = mock(CameraDao.class);
    private final LiveRelayService liveRelayService = mock(LiveRelayService.class);
    /** 探测结果由测试控制：集合内的 "host:port" 视为可达。 */
    private final Set<String> reachableTargets = ConcurrentHashMap.newKeySet();
    private final CameraStatusScanService service = new CameraStatusScanService(cameraDao, liveRelayService) {
        @Override
        protected boolean isReachable(String host, int port) {
            return reachableTargets.contains(host + ":" + port);
        }
    };

    @Test
    void runningCameraUnreachableIsMarkedOffline() {
        CameraEntity camera = camera("RUNNING", "rtsp://10.0.0.1:554/Streaming/Channels/101");
        when(cameraDao.selectAllOrdered()).thenReturn(List.of(camera));

        service.scanOnce();

        verify(cameraDao).updateStatus(camera.getId(), "OFFLINE");
        verifyNoInteractions(liveRelayService);
    }

    @Test
    void offlineCameraReachableAgainIsMarkedRunningAndProxyRestored() {
        CameraEntity camera = camera("OFFLINE", "rtsp://10.0.0.2:554/Streaming/Channels/101");
        reachableTargets.add("10.0.0.2:554");
        when(cameraDao.selectAllOrdered()).thenReturn(List.of(camera));

        service.scanOnce();

        verify(cameraDao).updateStatus(camera.getId(), "RUNNING");
        verify(liveRelayService).addZlmediakitProxy(camera.getSourceUrl(), camera.getStreamName());
        // 海康主码流可推导子码流：恢复时一并重挂子码流代理
        verify(liveRelayService).addZlmediakitProxy(
                "rtsp://10.0.0.2:554/Streaming/Channels/102", camera.getStreamName() + "-sub");
    }

    @Test
    void stoppedCameraIsNeverProbedNorUpdated() {
        CameraEntity camera = camera("STOPPED", "rtsp://10.0.0.3:554/Streaming/Channels/101");
        reachableTargets.add("10.0.0.3:554");
        when(cameraDao.selectAllOrdered()).thenReturn(List.of(camera));

        service.scanOnce();

        verify(cameraDao, never()).updateStatus(camera.getId(), "RUNNING");
        verify(cameraDao, never()).updateStatus(camera.getId(), "OFFLINE");
        verifyNoInteractions(liveRelayService);
    }

    @Test
    void runningCameraStillReachableKeepsStatusWithoutWrites() {
        CameraEntity camera = camera("RUNNING", "rtsp://10.0.0.4:554/Streaming/Channels/101");
        reachableTargets.add("10.0.0.4:554");
        when(cameraDao.selectAllOrdered()).thenReturn(List.of(camera));

        service.scanOnce();

        verify(cameraDao, never()).updateStatus(camera.getId(), "RUNNING");
        verify(cameraDao, never()).updateStatus(camera.getId(), "OFFLINE");
        verifyNoInteractions(liveRelayService);
    }

    @Test
    void camerasWithInternalOrUnparseableSourceUrlAreSkipped() {
        CameraEntity push = camera("RUNNING", "rtmp://zlm/live/push1");
        CameraEntity blank = camera("RUNNING", "");
        CameraEntity noScheme = camera("RUNNING", "not-a-url");
        when(cameraDao.selectAllOrdered()).thenReturn(List.of(push, blank, noScheme));

        service.scanOnce();

        verify(cameraDao, never()).updateStatus(push.getId(), "OFFLINE");
        verify(cameraDao, never()).updateStatus(blank.getId(), "OFFLINE");
        verify(cameraDao, never()).updateStatus(noScheme.getId(), "OFFLINE");
        verifyNoInteractions(liveRelayService);
    }

    private static CameraEntity camera(String status, String sourceUrl) {
        CameraEntity entity = new CameraEntity();
        entity.setId(UUID.randomUUID());
        entity.setName("测试摄像头");
        entity.setSourceUrl(sourceUrl);
        entity.setStreamName("cam-" + UUID.randomUUID());
        entity.setStatus(status);
        return entity;
    }
}
