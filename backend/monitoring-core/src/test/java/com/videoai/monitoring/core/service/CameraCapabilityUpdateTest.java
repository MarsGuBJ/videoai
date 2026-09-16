package com.videoai.monitoring.core.service;

import com.videoai.monitoring.common.dto.CameraUpdateRequest;
import com.videoai.monitoring.common.vo.CameraResponse;
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

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 批量能力配置链路回归：PATCH 仅携带能力开关时，update 将开关写入落库实体，
 * 响应（编辑页/弹窗回填的数据源）能原样还原勾选状态。
 */
class CameraCapabilityUpdateTest {

    private final CameraDao dao = mock(CameraDao.class);
    private final CameraService service = new CameraServiceImpl(
            dao, properties(), mock(ZlmClient.class), mock(LiveRelayService.class), mock(PreviewRelayManager.class));

    private static VideoAiProperties properties() {
        return new VideoAiProperties(
                new VideoAiProperties.Zlm("http://zlm", "http://zlm", "secret", "rtmp://zlm", "rtmp://zlm"),
                null, null, null, null, null, null, "", "", "", "ffmpeg");
    }

    private static CameraEntity entity(UUID id) {
        CameraEntity entity = new CameraEntity();
        entity.setId(id);
        entity.setName("摄像机A");
        entity.setSourceUrl("rtsp://192.168.1.64:554/Streaming/Channels/101");
        entity.setStreamApp("live");
        entity.setStreamName("cam-a");
        entity.setStatus("STOPPED");
        entity.setCreatedAt(OffsetDateTime.now());
        entity.setUpdatedAt(OffsetDateTime.now());
        return entity;
    }

    private static CameraUpdateRequest capabilityRequest(Boolean video, Boolean audio, Boolean talkback,
                                                         Boolean ptz, Boolean smart, Boolean alarmIo) {
        return new CameraUpdateRequest(null, null, null, null, null, null, null, null, null, null,
                null, null, null, null, null, null, video, audio, talkback, ptz, smart, alarmIo,
                null, null, null, null, null, null, null, null);
    }

    @Test
    void updatePersistsCapabilityFlagsAndResponseRestoresThem() {
        UUID id = UUID.randomUUID();
        CameraEntity stored = entity(id);
        when(dao.selectById(id)).thenReturn(stored);

        CameraResponse response = service.update(id, capabilityRequest(true, true, false, true, false, true));

        ArgumentCaptor<CameraEntity> captor = ArgumentCaptor.forClass(CameraEntity.class);
        verify(dao).updateCamera(captor.capture());
        CameraEntity updated = captor.getValue();
        assertTrue(updated.getVideoPreviewEnabled());
        assertTrue(updated.getAudioEnabled());
        assertFalse(updated.getTalkbackEnabled());
        assertTrue(updated.getPtzEnabled());
        assertFalse(updated.getSmartAnalysisEnabled());
        assertTrue(updated.getAlarmIoEnabled());

        // 模拟落库后再次查询：编辑页回填所用的响应必须与勾选状态一致
        stored.setVideoPreviewEnabled(true);
        stored.setAudioEnabled(true);
        stored.setTalkbackEnabled(false);
        stored.setPtzEnabled(true);
        stored.setSmartAnalysisEnabled(false);
        stored.setAlarmIoEnabled(true);
        CameraResponse restored = service.get(id);
        assertTrue(restored.videoPreviewEnabled());
        assertTrue(restored.audioEnabled());
        assertFalse(restored.talkbackEnabled());
        assertTrue(restored.ptzEnabled());
        assertFalse(restored.smartAnalysisEnabled());
        assertTrue(restored.alarmIoEnabled());
    }

    @Test
    void updateKeepsCapabilityFlagsWhenRequestOmitsThem() {
        UUID id = UUID.randomUUID();
        CameraEntity stored = entity(id);
        stored.setVideoPreviewEnabled(true);
        stored.setPtzEnabled(true);
        when(dao.selectById(id)).thenReturn(stored);

        service.update(id, capabilityRequest(null, null, null, null, null, null));

        ArgumentCaptor<CameraEntity> captor = ArgumentCaptor.forClass(CameraEntity.class);
        verify(dao).updateCamera(captor.capture());
        CameraEntity updated = captor.getValue();
        assertTrue(updated.getVideoPreviewEnabled());
        assertTrue(updated.getPtzEnabled());
        assertEquals(Boolean.FALSE, updated.getAudioEnabled() == null ? Boolean.FALSE : updated.getAudioEnabled());
    }

    @Test
    void getMapsEntityFlagsToResponse() {
        UUID id = UUID.randomUUID();
        CameraEntity stored = entity(id);
        stored.setSmartAnalysisEnabled(true);
        when(dao.selectById(id)).thenReturn(stored);

        CameraResponse response = service.get(id);

        assertFalse(response.videoPreviewEnabled());
        assertFalse(response.audioEnabled());
        assertFalse(response.talkbackEnabled());
        assertFalse(response.ptzEnabled());
        assertTrue(response.smartAnalysisEnabled());
        assertFalse(response.alarmIoEnabled());
    }
}
