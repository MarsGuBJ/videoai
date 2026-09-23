package com.videoai.monitoring.core.controller;

import com.videoai.monitoring.common.vo.CameraResponse;
import com.videoai.monitoring.core.config.VideoAiProperties;
import com.videoai.monitoring.core.service.CameraService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * /api/live/{streamName}.live.flv 对未开播摄像头应自动开播（按需拉流），
 * 开播失败时保留 start() 抛出的原始状态码。
 */
class MediaStreamControllerTest {

    private final CameraService cameraService = mock(CameraService.class);
    private final VideoAiProperties properties = mock(VideoAiProperties.class);

    private final MediaStreamController controller =
            new MediaStreamController(cameraService, properties);

    @BeforeEach
    void setUp() {
        // 127.0.0.1:1 必然连接被拒：requirePreviewCamera 之后的代理阶段快速失败，
        // 测试只关注其之前的自动开播行为
        when(properties.zlm()).thenReturn(new VideoAiProperties.Zlm(
                "http://127.0.0.1:1", "http://127.0.0.1:1", "secret",
                "rtmp://127.0.0.1:1935/live", "rtmp://127.0.0.1:1935/preview"));
        when(properties.preview()).thenReturn(new VideoAiProperties.Preview(10, 50, "ffmpeg.cmd_preview_h264"));
    }

    @Test
    void stoppedCameraIsAutoStartedBeforeProxying() {
        UUID id = UUID.randomUUID();
        when(cameraService.findByStreamName("stream-1"))
                .thenReturn(List.of(camera(id, "STOPPED", "rtsp://10.0.0.1:554/Streaming/Channels/101")));
        when(cameraService.start(id)).thenReturn(camera(id, "RUNNING", "rtsp://10.0.0.1:554/Streaming/Channels/101"));

        ResponseStatusException exception =
                assertThrows(ResponseStatusException.class, () -> controller.proxyFlvStream("stream-1"));

        assertEquals(HttpStatus.BAD_GATEWAY, exception.getStatusCode());
        verify(cameraService).start(id);
    }

    @Test
    void runningCameraIsNotRestarted() {
        UUID id = UUID.randomUUID();
        when(cameraService.findByStreamName("stream-1"))
                .thenReturn(List.of(camera(id, "RUNNING", "rtsp://10.0.0.1:554/Streaming/Channels/101")));

        ResponseStatusException exception =
                assertThrows(ResponseStatusException.class, () -> controller.proxyFlvStream("stream-1"));

        assertEquals(HttpStatus.BAD_GATEWAY, exception.getStatusCode());
        verify(cameraService, never()).start(any());
    }

    @Test
    void startFailureKeepsOriginalStatus() {
        UUID id = UUID.randomUUID();
        when(cameraService.findByStreamName("stream-1"))
                .thenReturn(List.of(camera(id, "STOPPED", "rtsp://10.0.0.1:554/Streaming/Channels/101")));
        when(cameraService.start(id)).thenThrow(new ResponseStatusException(HttpStatus.CONFLICT, "设备拉流失败"));

        ResponseStatusException exception =
                assertThrows(ResponseStatusException.class, () -> controller.proxyFlvStream("stream-1"));

        assertEquals(HttpStatus.CONFLICT, exception.getStatusCode());
    }

    @Test
    void nonRtspSourceIsRejectedWithoutStart() {
        UUID id = UUID.randomUUID();
        when(cameraService.findByStreamName("stream-1"))
                .thenReturn(List.of(camera(id, "STOPPED", "http://10.0.0.1/live.flv")));

        ResponseStatusException exception =
                assertThrows(ResponseStatusException.class, () -> controller.proxyFlvStream("stream-1"));

        assertEquals(HttpStatus.BAD_REQUEST, exception.getStatusCode());
        verify(cameraService, never()).start(any());
    }

    @Test
    void unknownStreamNameIsNotFound() {
        when(cameraService.findByStreamName("missing")).thenReturn(List.of());

        ResponseStatusException exception =
                assertThrows(ResponseStatusException.class, () -> controller.proxyFlvStream("missing"));

        assertEquals(HttpStatus.NOT_FOUND, exception.getStatusCode());
    }

    private static CameraResponse camera(UUID id, String status, String sourceUrl) {
        return new CameraResponse(
                id, "测试设备", sourceUrl, "live", "stream-1", null,
                null, null, status, "ONLINE", null, OffsetDateTime.now(), OffsetDateTime.now(),
                null, null, null, null, null, null, null, null, null, null, null, null,
                false, false, false, false, false, false, false, null, null,
                null, null, null, null, null, null, null);
    }
}
