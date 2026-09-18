package com.videoai.monitoring.core.service;

import com.videoai.monitoring.common.dto.CameraCreateRequest;
import com.videoai.monitoring.common.dto.CameraUpdateRequest;
import com.videoai.monitoring.core.client.ZlmClient;
import com.videoai.monitoring.core.config.VideoAiProperties;
import com.videoai.monitoring.core.dao.CameraDao;
import com.videoai.monitoring.core.entity.CameraEntity;
import com.videoai.monitoring.core.service.impl.CameraServiceImpl;
import com.videoai.monitoring.core.service.preview.PreviewRelayManager;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.time.OffsetDateTime;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * cameras.area 写入规范化：create/update 落库前按 " / " 统一分隔符，
 * 与区域树完整路径口径一致（区域设备计数依赖该口径）。
 */
class CameraAreaNormalizeTest {

    private final CameraDao dao = mock(CameraDao.class);
    private final CameraService service = new CameraServiceImpl(
            dao, properties(), mock(ZlmClient.class), mock(LiveRelayService.class), mock(PreviewRelayManager.class),
            mock(OpenSubscriptionService.class));

    private static VideoAiProperties properties() {
        return new VideoAiProperties(
                new VideoAiProperties.Zlm("http://zlm", "http://zlm", "secret", "rtmp://zlm", "rtmp://zlm"),
                null, null, null, null, null, null, "", "", "", "ffmpeg");
    }

    @Test
    void createNormalizesAreaSeparators() {
        AtomicReference<CameraEntity> inserted = new AtomicReference<>();
        doAnswer(invocation -> {
            inserted.set(invocation.getArgument(0));
            return 1;
        }).when(dao).insert(any(CameraEntity.class));
        when(dao.selectById(any(UUID.class))).thenAnswer(invocation -> inserted.get());

        service.create(new CameraCreateRequest(
                "摄像机A", "rtsp://192.168.1.64:554/Streaming/Channels/101", null, "赛迪电气/园区",
                null, null, null, null, null, null, null, null, null, null, null, null,
                null, null, null, null, null, null, null, null, null, null, null, null, null, null));

        ArgumentCaptor<CameraEntity> captor = ArgumentCaptor.forClass(CameraEntity.class);
        verify(dao).insert(captor.capture());
        assertEquals("赛迪电气 / 园区", captor.getValue().getArea());
    }

    @Test
    void updateNormalizesAreaSeparators() {
        UUID id = UUID.randomUUID();
        CameraEntity old = new CameraEntity();
        old.setId(id);
        old.setName("摄像机A");
        old.setSourceUrl("rtsp://192.168.1.64:554/Streaming/Channels/101");
        old.setStreamName("cam-a");
        old.setArea("办公楼");
        old.setStatus("STOPPED");
        old.setCreatedAt(OffsetDateTime.now());
        old.setUpdatedAt(OffsetDateTime.now());
        when(dao.selectById(id)).thenReturn(old);

        service.update(id, new CameraUpdateRequest(null, null, null, " 东区 /  一车间 ", null, null, null, null,
                null, null, null, null, null, null, null, null, null, null, null, null, null, null,
                null, null, null, null, null, null, null, null));

        ArgumentCaptor<CameraEntity> captor = ArgumentCaptor.forClass(CameraEntity.class);
        verify(dao).updateCamera(captor.capture());
        assertEquals("东区 / 一车间", captor.getValue().getArea());
    }
}
