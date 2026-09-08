package com.videoai.monitoring.core.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.videoai.monitoring.common.dto.CameraCreateRequest;
import com.videoai.monitoring.common.dto.CloudDeviceItem;
import com.videoai.monitoring.common.dto.CloudPlatformCreateRequest;
import com.videoai.monitoring.common.dto.CloudPlatformUpdateRequest;
import com.videoai.monitoring.common.dto.CloudSyncRequest;
import com.videoai.monitoring.common.vo.CameraResponse;
import com.videoai.monitoring.common.vo.CloudPlatformResponse;
import com.videoai.monitoring.common.vo.CloudSyncResultResponse;
import com.videoai.monitoring.core.dao.CloudPlatformDao;
import com.videoai.monitoring.core.entity.CloudPlatformEntity;
import com.videoai.monitoring.core.service.impl.CloudPlatformServiceImpl;
import org.junit.jupiter.api.Test;
import org.springframework.web.server.ResponseStatusException;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class CloudPlatformServiceTest {

    private final CloudPlatformDao dao = mock(CloudPlatformDao.class);
    private final CameraService cameraService = mock(CameraService.class);
    private final CloudPlatformService service = new CloudPlatformServiceImpl(dao, cameraService, new ObjectMapper());

    private static CloudPlatformEntity entity(UUID id) {
        CloudPlatformEntity entity = new CloudPlatformEntity();
        entity.setId(id);
        entity.setName("平台A");
        entity.setType("GA1400");
        entity.setKey("app-key");
        entity.setSecret("app-secret");
        entity.setIp("192.168.1.10");
        entity.setPort("8080");
        entity.setCreatedAt(OffsetDateTime.now());
        entity.setUpdatedAt(OffsetDateTime.now());
        return entity;
    }

    @Test
    void listMapsEntitiesToResponses() {
        CloudPlatformEntity entity = entity(UUID.randomUUID());
        when(dao.selectAllOrdered()).thenReturn(List.of(entity));

        List<CloudPlatformResponse> result = service.list();

        assertEquals(1, result.size());
        CloudPlatformResponse response = result.get(0);
        assertEquals(entity.getId(), response.id());
        assertEquals(entity.getName(), response.name());
        assertEquals(entity.getType(), response.type());
        assertEquals(entity.getKey(), response.key());
        assertEquals(entity.getSecret(), response.secret());
        assertEquals(entity.getIp(), response.ip());
        assertEquals(entity.getPort(), response.port());
    }

    @Test
    void getThrowsNotFoundWhenMissing() {
        UUID id = UUID.randomUUID();
        when(dao.selectById(id)).thenReturn(null);

        assertThrows(ResponseStatusException.class, () -> service.get(id));
    }

    @Test
    void createGeneratesIdAndInserts() {
        UUID[] captured = new UUID[1];
        when(dao.insert(any(CloudPlatformEntity.class))).thenAnswer(invocation -> {
            CloudPlatformEntity entity = invocation.getArgument(0);
            captured[0] = entity.getId();
            return 1;
        });
        when(dao.selectById(any(UUID.class))).thenAnswer(invocation -> entity(invocation.getArgument(0)));

        CloudPlatformResponse response = service.create(
                new CloudPlatformCreateRequest("平台A", "GA1400", "app-key", "app-secret", "192.168.1.10", "8080"));

        assertEquals(captured[0], response.id());
        verify(dao).insert(any(CloudPlatformEntity.class));
    }

    @Test
    void updateThrowsNotFoundWhenMissing() {
        UUID id = UUID.randomUUID();
        when(dao.selectById(id)).thenReturn(null);

        assertThrows(ResponseStatusException.class, () -> service.update(id,
                new CloudPlatformUpdateRequest("平台A", "GA1400", "app-key", "app-secret", "192.168.1.10", "8080")));
        verify(dao, never()).updateCloudPlatform(any());
    }

    @Test
    void deleteSkipsMissingRow() {
        UUID id = UUID.randomUUID();
        when(dao.selectById(id)).thenReturn(null);

        service.delete(id);

        verify(dao, never()).deleteById(id);
    }

    private static CameraResponse camera(UUID id, String ip) {
        return new CameraResponse(
                id, "本地-" + ip, "rtsp://" + ip + "/stream", "live", "s-" + ip, null, null, "办公楼",
                "RUNNING", null, OffsetDateTime.now(), OffsetDateTime.now(),
                null, null, null, null, null, null, ip, "554",
                null, null, null, null, false, true, false, false, false, false, false);
    }

    private static CloudDeviceItem cloudDevice(String name, String ip) {
        return new CloudDeviceItem(name, "云端区域", "GB28181", ip, "554", "rtsp://" + ip + "/live", null, null);
    }

    @Test
    void diffByIpMarksNewAndUpdate() {
        UUID existing = UUID.randomUUID();

        List<CloudDeviceItem> items = CloudPlatformServiceImpl.diffByIp(
                List.of(cloudDevice("云端-北门", "10.0.0.1"), cloudDevice("云端-东门", "10.0.0.2")),
                List.of(camera(existing, "10.0.0.1")));

        assertEquals("update", items.get(0).status());
        assertEquals(existing, items.get(0).localCameraId());
        assertEquals("new", items.get(1).status());
        assertNull(items.get(1).localCameraId());
    }

    @Test
    void diffByIpIgnoresLocalCamerasWithoutIp() {
        List<CloudDeviceItem> items = CloudPlatformServiceImpl.diffByIp(
                List.of(cloudDevice("云端-北门", "10.0.0.1")),
                List.of(camera(UUID.randomUUID(), null)));

        assertEquals("new", items.get(0).status());
    }

    @Test
    void syncCreatesNewAndSkipsExistingWhenNotOverwrite() {
        UUID id = UUID.randomUUID();
        when(dao.selectById(id)).thenReturn(entity(id));
        when(cameraService.list()).thenReturn(List.of(camera(UUID.randomUUID(), "10.0.0.1")));

        CloudSyncResultResponse result = service.sync(id, new CloudSyncRequest(
                List.of(cloudDevice("云端-北门", "10.0.0.1"), cloudDevice("云端-东门", "10.0.0.2")),
                "园区总部",
                false));

        assertEquals(1, result.created());
        assertEquals(0, result.updated());
        assertEquals(1, result.skipped());
        verify(cameraService).create(any(CameraCreateRequest.class));
        verify(cameraService, never()).update(any(), any());
    }

    @Test
    void syncUpdatesExistingWhenOverwrite() {
        UUID id = UUID.randomUUID();
        UUID localId = UUID.randomUUID();
        when(dao.selectById(id)).thenReturn(entity(id));
        when(cameraService.list()).thenReturn(List.of(camera(localId, "10.0.0.1")));

        CloudSyncResultResponse result = service.sync(id, new CloudSyncRequest(
                List.of(cloudDevice("云端-北门", "10.0.0.1")),
                "园区总部",
                true));

        assertEquals(0, result.created());
        assertEquals(1, result.updated());
        verify(cameraService).update(eq(localId), any());
        verify(cameraService, never()).create(any());
    }

    @Test
    void syncSkipsNewDeviceWithoutSourceUrl() {
        UUID id = UUID.randomUUID();
        when(dao.selectById(id)).thenReturn(entity(id));
        when(cameraService.list()).thenReturn(List.of());

        CloudSyncResultResponse result = service.sync(id, new CloudSyncRequest(
                List.of(new CloudDeviceItem("云端-北门", "云端区域", "GB28181", "10.0.0.9", "554", null, null, null)),
                null,
                true));

        assertEquals(0, result.created());
        assertEquals(1, result.skipped());
        verify(cameraService, never()).create(any());
    }
}
