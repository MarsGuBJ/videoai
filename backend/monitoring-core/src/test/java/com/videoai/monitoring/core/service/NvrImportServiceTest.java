package com.videoai.monitoring.core.service;

import com.videoai.monitoring.common.dto.CameraCreateRequest;
import com.videoai.monitoring.common.dto.NvrImportItem;
import com.videoai.monitoring.common.dto.NvrImportPrecheckRequest;
import com.videoai.monitoring.common.dto.NvrImportSyncRequest;
import com.videoai.monitoring.common.vo.CameraResponse;
import com.videoai.monitoring.common.vo.CloudSyncResultResponse;
import com.videoai.monitoring.common.vo.NvrImportPrecheckResponse;
import com.videoai.monitoring.core.client.NvrChannelClient;
import com.videoai.monitoring.core.client.NvrChannelClient.NvrChannel;
import com.videoai.monitoring.core.client.NvrChannelClient.NvrDevice;
import com.videoai.monitoring.core.service.impl.NvrImportServiceImpl;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class NvrImportServiceTest {

    private final NvrChannelClient nvrChannelClient = mock(NvrChannelClient.class);
    private final CameraService cameraService = mock(CameraService.class);
    private final NvrImportService service = new NvrImportServiceImpl(nvrChannelClient, cameraService);

    private static CameraResponse camera(UUID id, String ip) {
        return new CameraResponse(
                id, "本地-" + ip, "rtsp://" + ip + "/stream", "live", "s-" + ip, null, null, "办公楼",
                "RUNNING", "ONLINE", null, OffsetDateTime.now(), OffsetDateTime.now(),
                null, null, null, null, null, null, ip, "554",
                null, null, null, null, false, true, false, false, false, false, false, null, null,
                null, null, null, null, null, null, null);
    }

    private static NvrDevice device(NvrChannel... channels) {
        return new NvrDevice(List.of(channels), 554);
    }

    @Test
    void precheckMergesChannelsFromMultipleDevices() {
        when(cameraService.list()).thenReturn(List.of());
        when(nvrChannelClient.fetchDevice(eq("10.0.0.1"), eq(80), anyString(), anyString()))
                .thenReturn(device(new NvrChannel(1, 101, "南门枪机", "10.10.0.93")));
        when(nvrChannelClient.fetchDevice(eq("10.0.0.2"), eq(8080), anyString(), anyString()))
                .thenReturn(device(new NvrChannel(1, 101, "北门枪机", "10.10.0.94")));

        NvrImportPrecheckResponse result = service.precheck(new NvrImportPrecheckRequest(
                new String[]{"10.0.0.1", "10.0.0.2:8080"}, "admin", "secret"));

        assertEquals(2, result.items().size());
        assertEquals(2, result.newCount());
        assertEquals(0, result.updateCount());
        assertTrue(result.failures().isEmpty());
        NvrImportItem first = result.items().get(0);
        assertEquals("南门枪机", first.name());
        assertEquals("10.10.0.93", first.ip());
        assertEquals("101", first.trackId());
        assertEquals("RTSP 拉流", first.protocol());
        assertEquals("rtsp://admin:secret@10.0.0.1:554/Streaming/Channels/101", first.sourceUrl());
    }

    @Test
    void precheckMarksUpdateWhenLocalCameraHasSameIp() {
        UUID localId = UUID.randomUUID();
        when(cameraService.list()).thenReturn(List.of(camera(localId, "10.10.0.93")));
        when(nvrChannelClient.fetchDevice(anyString(), anyInt(), anyString(), anyString()))
                .thenReturn(device(new NvrChannel(1, 101, "南门枪机", "10.10.0.93")));

        NvrImportPrecheckResponse result = service.precheck(new NvrImportPrecheckRequest(
                new String[]{"10.0.0.1"}, "admin", "secret"));

        assertEquals(1, result.updateCount());
        assertEquals("update", result.items().get(0).status());
        assertEquals(localId.toString(), result.items().get(0).localCameraId());
    }

    @Test
    void precheckCollectsFailureWithoutBlockingOtherDevices() {
        when(cameraService.list()).thenReturn(List.of());
        when(nvrChannelClient.fetchDevice(eq("10.0.0.1"), anyInt(), anyString(), anyString()))
                .thenThrow(new ResponseStatusException(HttpStatus.BAD_GATEWAY, "NVR 10.0.0.1 设备信息读取失败（HTTP 401），请检查地址与账号密码"));
        when(nvrChannelClient.fetchDevice(eq("10.0.0.2"), anyInt(), anyString(), anyString()))
                .thenReturn(device(new NvrChannel(2, 201, "东门枪机", "10.10.0.95")));

        NvrImportPrecheckResponse result = service.precheck(new NvrImportPrecheckRequest(
                new String[]{"10.0.0.1", "10.0.0.2"}, "admin", "secret"));

        assertEquals(1, result.items().size());
        assertEquals(1, result.failures().size());
        assertEquals("10.0.0.1", result.failures().get(0).host());
    }

    @Test
    void precheckEncodesCredentialsInSourceUrl() {
        when(cameraService.list()).thenReturn(List.of());
        when(nvrChannelClient.fetchDevice(anyString(), anyInt(), anyString(), anyString()))
                .thenReturn(device(new NvrChannel(1, 101, "南门枪机", "10.10.0.93")));

        NvrImportPrecheckResponse result = service.precheck(new NvrImportPrecheckRequest(
                new String[]{"10.0.0.1"}, "ad min", "p@ss:word"));

        assertEquals("rtsp://ad%20min:p%40ss%3Aword@10.0.0.1:554/Streaming/Channels/101",
                result.items().get(0).sourceUrl());
    }

    @Test
    void syncCreatesNewAndSkipsExistingWhenNotOverwrite() {
        UUID localId = UUID.randomUUID();
        when(cameraService.list()).thenReturn(List.of(camera(localId, "10.10.0.93")));

        CloudSyncResultResponse result = service.sync(new NvrImportSyncRequest(
                List.of(
                        new NvrImportItem("南门枪机", "10.10.0.93", "554", "1", "101", "10.0.0.1",
                                "rtsp://admin:secret@10.0.0.1:554/Streaming/Channels/101", "RTSP 拉流", "update", localId.toString()),
                        new NvrImportItem("北门枪机", "10.10.0.94", "554", "1", "101", "10.0.0.1",
                                "rtsp://admin:secret@10.0.0.1:554/Streaming/Channels/102", "RTSP 拉流", "new", null)),
                "园区总部", false, "admin", "secret"));

        assertEquals(1, result.created());
        assertEquals(0, result.updated());
        assertEquals(1, result.skipped());
        ArgumentCaptor<CameraCreateRequest> captor = ArgumentCaptor.forClass(CameraCreateRequest.class);
        verify(cameraService).create(captor.capture());
        CameraCreateRequest created = captor.getValue();
        assertEquals("北门枪机", created.name());
        assertEquals("园区总部", created.area());
        assertEquals("1", created.nvrChannel());
        assertEquals("101", created.nvrTrackId());
        assertEquals("主码流", created.nvrStreamType());
        assertEquals("海康威视", created.vendor());
        assertEquals("10.10.0.94", created.ip());
        assertEquals("admin", created.username());
        assertEquals("secret", created.password());
        verify(cameraService, never()).update(any(), any());
    }

    @Test
    void syncUpdatesExistingWhenOverwrite() {
        UUID localId = UUID.randomUUID();
        when(cameraService.list()).thenReturn(List.of(camera(localId, "10.10.0.93")));

        CloudSyncResultResponse result = service.sync(new NvrImportSyncRequest(
                List.of(new NvrImportItem("南门枪机", "10.10.0.93", "554", "1", "101", "10.0.0.1",
                        "rtsp://admin:secret@10.0.0.1:554/Streaming/Channels/101", "RTSP 拉流", "update", localId.toString())),
                null, true, "admin", "secret"));

        assertEquals(0, result.created());
        assertEquals(1, result.updated());
        verify(cameraService).update(eq(localId), any());
        verify(cameraService, never()).create(any());
    }

    @Test
    void syncSkipsNewItemWithoutSourceUrl() {
        when(cameraService.list()).thenReturn(List.of());

        CloudSyncResultResponse result = service.sync(new NvrImportSyncRequest(
                List.of(new NvrImportItem("无名通道", null, "554", "3", "301", "10.0.0.1",
                        null, "RTSP 拉流", "new", null)),
                null, true, "admin", "secret"));

        assertEquals(0, result.created());
        assertEquals(1, result.skipped());
        verify(cameraService, never()).create(any());
    }

    @Test
    void parseHostPortSupportsIpAndIpWithPort() {
        assertEquals(new NvrImportServiceImpl.HostPort("10.0.0.1", 80), NvrImportServiceImpl.parseHostPort("10.0.0.1"));
        assertEquals(new NvrImportServiceImpl.HostPort("10.0.0.1", 8080), NvrImportServiceImpl.parseHostPort("10.0.0.1:8080"));
        assertThrows(ResponseStatusException.class, () -> NvrImportServiceImpl.parseHostPort("10.0.0.1:abc"));
        assertThrows(ResponseStatusException.class, () -> NvrImportServiceImpl.parseHostPort("10.0.0.1:70000"));
    }
}
