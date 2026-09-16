package com.videoai.monitoring.core.service.impl;

import com.videoai.monitoring.core.dao.CameraDao;
import com.videoai.monitoring.core.entity.CameraEntity;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

class CameraStatusScanServiceTest {

    private final CameraDao cameraDao = mock(CameraDao.class);
    /** 探测结果由测试控制：集合内的 "host:port" 视为可达。 */
    private final Set<String> reachableTargets = ConcurrentHashMap.newKeySet();
    private final CameraStatusScanService service = new CameraStatusScanService(cameraDao) {
        @Override
        protected boolean isReachable(String host, int port) {
            return reachableTargets.contains(host + ":" + port);
        }
    };

    @Test
    void probesEveryDeviceIncludingStoppedAndDisabled() {
        CameraEntity running = camera("RUNNING", "ONLINE", "rtsp://10.0.0.1:554/Streaming/Channels/101");
        CameraEntity stopped = camera("STOPPED", "UNKNOWN", "rtsp://10.0.0.2:554/Streaming/Channels/101");
        CameraEntity disabled = camera("DISABLED", "ONLINE", "rtsp://10.0.0.3:554/Streaming/Channels/101");
        reachableTargets.add("10.0.0.1:554");
        reachableTargets.add("10.0.0.2:554");
        when(cameraDao.selectAllOrdered()).thenReturn(List.of(running, stopped, disabled));

        CameraStatusScanService.ScanResult result = service.scanOnce();

        assertEquals(3, result.total());
        assertEquals(2, result.online());
        assertEquals(1, result.offline());
        assertEquals(0, result.unknown());
        assertEquals(2, result.changed());
        // 已停止/已停用的设备同样纳入探测：可达写 ONLINE、不可达写 OFFLINE
        verify(cameraDao).updateOnlineStatus(stopped.getId(), "ONLINE");
        verify(cameraDao).updateOnlineStatus(disabled.getId(), "OFFLINE");
        verify(cameraDao, never()).updateOnlineStatus(running.getId(), "ONLINE");
        // 扫描不再改写拉流状态
        verify(cameraDao, never()).updateStatus(any(), anyString());
    }

    @Test
    void stoppedDeviceUnreachableIsMarkedOffline() {
        CameraEntity stopped = camera("STOPPED", "ONLINE", "rtsp://10.0.0.9:554/Streaming/Channels/101");
        when(cameraDao.selectAllOrdered()).thenReturn(List.of(stopped));

        CameraStatusScanService.ScanResult result = service.scanOnce();

        assertEquals(1, result.offline());
        verify(cameraDao).updateOnlineStatus(stopped.getId(), "OFFLINE");
    }

    @Test
    void internalOrUnparseableSourceBecomesUnknown() {
        CameraEntity push = camera("RUNNING", "ONLINE", "rtmp://zlm/live/push1");
        CameraEntity blank = camera("STOPPED", "OFFLINE", "");
        CameraEntity noScheme = camera("RUNNING", "ONLINE", "not-a-url");
        when(cameraDao.selectAllOrdered()).thenReturn(List.of(push, blank, noScheme));

        CameraStatusScanService.ScanResult result = service.scanOnce();

        assertEquals(3, result.unknown());
        assertEquals(0, result.online());
        assertEquals(0, result.offline());
        verify(cameraDao).updateOnlineStatus(push.getId(), "UNKNOWN");
        verify(cameraDao).updateOnlineStatus(blank.getId(), "UNKNOWN");
        verify(cameraDao).updateOnlineStatus(noScheme.getId(), "UNKNOWN");
    }

    @Test
    void unchangedStatusIsNotWritten() {
        CameraEntity camera = camera("RUNNING", "ONLINE", "rtsp://10.0.0.4:554/Streaming/Channels/101");
        reachableTargets.add("10.0.0.4:554");
        when(cameraDao.selectAllOrdered()).thenReturn(List.of(camera));

        CameraStatusScanService.ScanResult result = service.scanOnce();

        assertEquals(1, result.online());
        assertEquals(0, result.changed());
        verify(cameraDao, never()).updateOnlineStatus(any(), anyString());
        verify(cameraDao, never()).updateStatus(any(), anyString());
    }

    private static CameraEntity camera(String status, String onlineStatus, String sourceUrl) {
        CameraEntity entity = new CameraEntity();
        entity.setId(UUID.randomUUID());
        entity.setName("测试摄像头");
        entity.setSourceUrl(sourceUrl);
        entity.setStreamName("cam-" + UUID.randomUUID());
        entity.setStatus(status);
        entity.setOnlineStatus(onlineStatus);
        return entity;
    }
}
