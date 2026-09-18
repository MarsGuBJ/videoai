package com.videoai.monitoring.core.service;

import com.videoai.monitoring.common.dto.CameraCreateRequest;
import com.videoai.monitoring.common.dto.CameraUpdateRequest;
import com.videoai.monitoring.common.vo.CameraResponse;
import com.videoai.monitoring.core.client.DeviceSourceProbe;
import com.videoai.monitoring.core.client.ZlmClient;
import com.videoai.monitoring.core.config.VideoAiProperties;
import com.videoai.monitoring.core.dao.CameraDao;
import com.videoai.monitoring.core.entity.CameraEntity;
import com.videoai.monitoring.core.service.impl.CameraServiceImpl;
import com.videoai.monitoring.core.service.preview.PreviewRelayManager;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 新增设备页去掉编号/序列号输入框后的回归：
 * 设备编号留空时按 CAM%05d 自动分配；序列号回取的解析与可解析性判断。
 */
class CameraDeviceCodeGenerateTest {

    private final CameraDao dao = mock(CameraDao.class);
    private final CameraService service = new CameraServiceImpl(
            dao, properties(), mock(ZlmClient.class), mock(LiveRelayService.class), mock(PreviewRelayManager.class),
            mock(OpenSubscriptionService.class));

    private static VideoAiProperties properties() {
        return new VideoAiProperties(
                new VideoAiProperties.Zlm("http://zlm", "http://zlm", "secret", "rtmp://zlm", "rtmp://zlm"),
                null, null, null, null, null, null, "", "", "", "ffmpeg");
    }

    /** 无内嵌凭据的拉流地址：不会触发序列号后台回取。 */
    private static CameraCreateRequest createRequest(String deviceCode) {
        return new CameraCreateRequest("摄像机A", "rtsp://192.168.1.64:554/Streaming/Channels/101",
                null, null, null, null, null, null, null, null, null, null, null, null,
                deviceCode, null, null, null, null, null, null, null,
                null, null, null, null, null, null, null, null);
    }

    private AtomicReference<CameraEntity> stubInsertAndGet() {
        AtomicReference<CameraEntity> inserted = new AtomicReference<>();
        doAnswer(invocation -> {
            inserted.set(invocation.getArgument(0));
            return 1;
        }).when(dao).insert(any(CameraEntity.class));
        when(dao.selectById(any())).thenAnswer(invocation -> inserted.get());
        return inserted;
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

    @Test
    void createAssignsCam00001WhenNoExistingCodes() {
        when(dao.selectCamDeviceCodes()).thenReturn(List.of());
        AtomicReference<CameraEntity> inserted = stubInsertAndGet();

        CameraResponse response = service.create(createRequest(null));

        assertEquals("CAM00001", inserted.get().getDeviceCode());
        assertEquals("CAM00001", response.deviceCode());
    }

    @Test
    void createAssignsNextSequenceBasedOnMaxExistingCode() {
        when(dao.selectCamDeviceCodes()).thenReturn(List.of("CAM00001", "CAM00007", "CAM00003"));
        AtomicReference<CameraEntity> inserted = stubInsertAndGet();

        CameraResponse response = service.create(createRequest("  "));

        assertEquals("CAM00008", inserted.get().getDeviceCode());
        assertEquals("CAM00008", response.deviceCode());
    }

    @Test
    void createKeepsExplicitDeviceCode() {
        when(dao.selectCamDeviceCodes()).thenReturn(List.of("CAM00007"));
        AtomicReference<CameraEntity> inserted = stubInsertAndGet();

        CameraResponse response = service.create(createRequest("DEV-100"));

        assertEquals("DEV-100", inserted.get().getDeviceCode());
        assertEquals("DEV-100", response.deviceCode());
    }

    @Test
    void serialNumberResolvableOnlyWithEmbeddedCredentials() {
        assertTrue(DeviceSourceProbe.isResolvable("rtsp://admin:pass123@192.168.1.64:554/Streaming/Channels/101"));
        assertFalse(DeviceSourceProbe.isResolvable("rtsp://192.168.1.64:554/Streaming/Channels/101"));
        assertFalse(DeviceSourceProbe.isResolvable("rtsp://admin@192.168.1.64:554/live"));
        assertFalse(DeviceSourceProbe.isResolvable(null));
        assertFalse(DeviceSourceProbe.isResolvable(""));
    }

    @Test
    void updateAssignsDeviceCodeWhenBlank() {
        UUID id = UUID.randomUUID();
        CameraEntity stored = entity(id);
        stored.setDeviceCode(""); // 历史遗留空串
        when(dao.selectById(id)).thenReturn(stored);
        when(dao.selectCamDeviceCodes()).thenReturn(List.of("CAM00003"));

        // 全 null 的 PATCH：不传 deviceCode
        service.update(id, new com.videoai.monitoring.common.dto.CameraUpdateRequest(
                null, null, null, null, null, null, null, null, null, null,
                null, null, null, null, null, null, null, null, null, null,
                null, null, null, null, null, null, null, null, null, null));

        ArgumentCaptor<CameraEntity> captor = ArgumentCaptor.forClass(CameraEntity.class);
        verify(dao).updateCamera(captor.capture());
        assertEquals("CAM00004", captor.getValue().getDeviceCode());
    }

    @Test
    void updateKeepsExistingDeviceCode() {
        UUID id = UUID.randomUUID();
        CameraEntity stored = entity(id);
        stored.setDeviceCode("DEV-100");
        when(dao.selectById(id)).thenReturn(stored);

        service.update(id, new com.videoai.monitoring.common.dto.CameraUpdateRequest(
                null, null, null, null, null, null, null, null, null, null,
                null, null, null, null, null, null, null, null, null, null,
                null, null, null, null, null, null, null, null, null, null));

        ArgumentCaptor<CameraEntity> captor = ArgumentCaptor.forClass(CameraEntity.class);
        verify(dao).updateCamera(captor.capture());
        assertEquals("DEV-100", captor.getValue().getDeviceCode());
    }

    @Test
    void parseSerialNumberFromDeviceInfoXml() {
        String xml = "<?xml version=\"1.0\"?><DeviceInfo><deviceName>IPC</deviceName>"
                + "<serialNumber>DS-2CD1234-I20240101AAACH123456789</serialNumber></DeviceInfo>";
        assertEquals(Optional.of("DS-2CD1234-I20240101AAACH123456789"),
                DeviceSourceProbe.parseSerialNumber(xml));
        assertEquals(Optional.empty(), DeviceSourceProbe.parseSerialNumber("<DeviceInfo/>"));
        assertEquals(Optional.empty(), DeviceSourceProbe.parseSerialNumber(null));
    }

    @Test
    void parseSourceExtractsConnectionParts() {
        DeviceSourceProbe.ParsedSource full = DeviceSourceProbe.parseSource("rtsp://admin:pass123@192.168.1.64:554/Streaming/Channels/101");
        assertEquals("192.168.1.64", full.host());
        assertEquals(554, full.port());
        assertEquals("admin", full.username());
        assertEquals("pass123", full.password());

        // 缺省端口按协议补默认
        DeviceSourceProbe.ParsedSource noPort = DeviceSourceProbe.parseSource("rtsp://192.168.1.64/live");
        assertEquals(554, noPort.port());
        assertEquals(null, noPort.username());

        // userinfo 百分号解码：%2B → '+'，且字面 '+' 不被误转为空格
        DeviceSourceProbe.ParsedSource encoded = DeviceSourceProbe.parseSource("rtsp://admin:Zysd2026%2B@10.10.7.253:554/Streaming/Channels/201");
        assertEquals("Zysd2026+", encoded.password());

        assertEquals(null, DeviceSourceProbe.parseSource("not a url"));
        assertEquals(null, DeviceSourceProbe.parseSource(null));
    }
}
