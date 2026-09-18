package com.videoai.monitoring.core.service.impl;

import com.videoai.monitoring.common.vo.CameraResponse;
import com.videoai.monitoring.core.client.ZlmClient;
import com.videoai.monitoring.core.dao.CameraDao;
import com.videoai.monitoring.core.service.CameraService;
import com.videoai.monitoring.core.service.LiveRelayService;
import org.junit.jupiter.api.Test;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class StreamGuardServiceImplTest {

    private static final UUID CAMERA_ID = UUID.fromString("11111111-2222-3333-4444-555555555555");

    private final CameraService cameraService = mock(CameraService.class);
    private final LiveRelayService liveRelayService = mock(LiveRelayService.class);
    private final ZlmClient zlmClient = mock(ZlmClient.class);
    private final CameraDao cameraDao = mock(CameraDao.class);
    private final StreamGuardServiceImpl guard =
            new StreamGuardServiceImpl(cameraService, liveRelayService, zlmClient, cameraDao);

    private void noActiveStreams() {
        when(zlmClient.mediaList()).thenReturn(Map.of("code", 0, "data", List.of()));
    }

    @Test
    void repeatedAttachFailureOnReachableDeviceStopsStreaming() {
        CameraResponse camera = camera("RUNNING", "ONLINE", null);
        when(cameraService.list()).thenReturn(List.of(camera));
        noActiveStreams();
        when(liveRelayService.addZlmediakitProxy(anyString(), anyString(), anyBoolean(), anyBoolean())).thenReturn(false);

        guard.reconcileStreams();
        guard.reconcileStreams();
        verify(cameraDao, never()).updateStatus(any(), anyString());

        guard.reconcileStreams();
        verify(cameraDao).updateStatus(CAMERA_ID, "STOPPED");
    }

    @Test
    void unreachableDeviceKeepsStreamingIntent() {
        CameraResponse camera = camera("RUNNING", "OFFLINE", null);
        when(cameraService.list()).thenReturn(List.of(camera));
        noActiveStreams();
        when(liveRelayService.addZlmediakitProxy(anyString(), anyString(), anyBoolean(), anyBoolean())).thenReturn(false);

        for (int i = 0; i < 5; i += 1) {
            guard.reconcileStreams();
        }

        // 设备不可达时不降级：保留 RUNNING 表示设备恢复后继续拉流
        verify(cameraDao, never()).updateStatus(any(), anyString());
    }

    @Test
    void successfulAttachResetsFailureCounter() {
        CameraResponse camera = camera("RUNNING", "ONLINE", null);
        when(cameraService.list()).thenReturn(List.of(camera));
        noActiveStreams();
        when(liveRelayService.addZlmediakitProxy(anyString(), anyString(), anyBoolean(), anyBoolean()))
                .thenReturn(false, false, true, false, false);

        for (int i = 0; i < 5; i += 1) {
            guard.reconcileStreams();
        }

        verify(cameraDao, never()).updateStatus(any(), anyString());
    }

    @Test
    void subStreamFailureDoesNotStopMainStream() {
        CameraResponse camera = camera("RUNNING", "ONLINE", "stream-1-sub");
        when(cameraService.list()).thenReturn(List.of(camera));
        noActiveStreams();
        when(liveRelayService.addZlmediakitProxy(anyString(), eq("stream-1"), anyBoolean(), anyBoolean())).thenReturn(true);
        when(liveRelayService.addZlmediakitProxy(anyString(), eq("stream-1-sub"), anyBoolean())).thenReturn(false);

        for (int i = 0; i < 5; i += 1) {
            guard.reconcileStreams();
        }

        verify(cameraDao, never()).updateStatus(any(), anyString());
    }

    @Test
    void stoppedCameraIsIgnored() {
        CameraResponse camera = camera("STOPPED", "ONLINE", null);
        when(cameraService.list()).thenReturn(List.of(camera));
        noActiveStreams();

        guard.reconcileStreams();

        verify(liveRelayService, never()).addZlmediakitProxy(anyString(), anyString(), anyBoolean(), anyBoolean());
        verify(cameraDao, never()).updateStatus(any(), anyString());
    }

    private static CameraResponse camera(String status, String onlineStatus, String subStreamName) {
        return new CameraResponse(
                CAMERA_ID, "测试设备", "rtsp://10.0.0.1:554/Streaming/Channels/101", "live", "stream-1", null,
                null, "办公楼", status, onlineStatus, null, OffsetDateTime.now(), OffsetDateTime.now(),
                null, null, null, null, null, null, "10.0.0.1", "554", null, null, null, null,
                false, true, false, false, false, false, false, subStreamName, null,
                null, null, null, null, null, null, null);
    }
}
