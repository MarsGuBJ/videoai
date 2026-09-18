package com.videoai.monitoring.core.service.impl;

import com.videoai.monitoring.core.client.ZlmClient;
import com.videoai.monitoring.core.config.VideoAiProperties;
import com.videoai.monitoring.core.dao.CameraDao;
import com.videoai.monitoring.core.entity.CameraEntity;
import com.videoai.monitoring.core.service.LiveRelayService;
import com.videoai.monitoring.core.service.OpenSubscriptionService;
import com.videoai.monitoring.core.service.preview.PreviewRelayManager;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.time.OffsetDateTime;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/** start() 必须先挂流成功再置 RUNNING，否则拉流服务拒绝地址时会出现"假在线"。 */
class CameraServiceImplStartTest {

    private final CameraDao cameraDao = mock(CameraDao.class);
    private final VideoAiProperties properties = mock(VideoAiProperties.class);
    private final ZlmClient zlmClient = mock(ZlmClient.class);
    private final LiveRelayService liveRelayService = mock(LiveRelayService.class);
    private final PreviewRelayManager previewRelayManager = mock(PreviewRelayManager.class);

    private final CameraServiceImpl service =
            new CameraServiceImpl(cameraDao, properties, zlmClient, liveRelayService, previewRelayManager,
                    mock(OpenSubscriptionService.class));

    @BeforeEach
    void setUp() {
        when(properties.zlm()).thenReturn(new VideoAiProperties.Zlm(
                "http://10.0.0.9:82", "http://10.0.0.9:82", "secret",
                "rtmp://10.0.0.9:1935/live", "rtmp://10.0.0.9:1935/preview"));
    }

    @Test
    void relayRejectionKeepsDeviceStoppedAndReportsConflict() {
        UUID id = UUID.randomUUID();
        when(cameraDao.selectById(id)).thenReturn(camera(id));
        when(liveRelayService.addZlmediakitProxy(anyString(), anyString(), anyBoolean(), anyBoolean())).thenReturn(false);

        ResponseStatusException exception =
                assertThrows(ResponseStatusException.class, () -> service.start(id));

        assertEquals(HttpStatus.CONFLICT, exception.getStatusCode());
        verify(cameraDao).updateStatus(id, "STOPPED");
        verify(cameraDao, never()).updateStatus(id, "RUNNING");
    }

    @Test
    void relayAcceptedMarksStreamingAndRegistersSubStream() {
        UUID id = UUID.randomUUID();
        when(cameraDao.selectById(id)).thenReturn(camera(id));
        when(liveRelayService.addZlmediakitProxy(anyString(), anyString(), anyBoolean(), anyBoolean())).thenReturn(true);

        service.start(id);

        verify(cameraDao).updateStatus(id, "RUNNING");
        verify(liveRelayService).addZlmediakitProxy("rtsp://10.0.0.1:554/Streaming/Channels/101", "stream-1", false, false);
        verify(liveRelayService).addZlmediakitProxy("rtsp://10.0.0.1:554/Streaming/Channels/102", "stream-1-sub");
    }

    private static CameraEntity camera(UUID id) {
        CameraEntity entity = new CameraEntity();
        entity.setId(id);
        entity.setName("测试设备");
        entity.setSourceUrl("rtsp://10.0.0.1:554/Streaming/Channels/101");
        entity.setStreamApp("live");
        entity.setStreamName("stream-1");
        entity.setStatus("STOPPED");
        entity.setOnlineStatus("ONLINE");
        entity.setCreatedAt(OffsetDateTime.now());
        entity.setUpdatedAt(OffsetDateTime.now());
        return entity;
    }
}
