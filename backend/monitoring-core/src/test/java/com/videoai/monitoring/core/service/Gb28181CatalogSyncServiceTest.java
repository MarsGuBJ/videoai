package com.videoai.monitoring.core.service;

import com.videoai.monitoring.common.dto.CameraCreateRequest;
import com.videoai.monitoring.common.dto.CameraUpdateRequest;
import com.videoai.monitoring.common.dto.CloudDeviceItem;
import com.videoai.monitoring.common.dto.CloudSyncRequest;
import com.videoai.monitoring.common.dto.Gb28181Config;
import com.videoai.monitoring.common.vo.AccessConfigResponse;
import com.videoai.monitoring.common.vo.CameraResponse;
import com.videoai.monitoring.common.vo.CloudSyncPrecheckResponse;
import com.videoai.monitoring.common.vo.CloudSyncResultResponse;
import com.videoai.monitoring.core.dao.Gb28181AccessConfigDao;
import com.videoai.monitoring.core.entity.Gb28181AccessConfigEntity;
import com.videoai.monitoring.core.service.impl.Gb28181CatalogSyncService;
import com.videoai.monitoring.core.support.Gb28181CatalogClient;
import com.videoai.monitoring.core.support.Gb28181CatalogClient.Gb28181CatalogDevice;
import com.videoai.monitoring.core.support.Gb28181CatalogClient.LocalSipConfig;
import com.videoai.monitoring.core.support.Gb28181CatalogClient.TargetServer;
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
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class Gb28181CatalogSyncServiceTest {

    private final Gb28181AccessConfigDao dao = mock(Gb28181AccessConfigDao.class);
    private final AccessConfigService accessConfigService = mock(AccessConfigService.class);
    private final CameraService cameraService = mock(CameraService.class);
    private final Gb28181CatalogClient catalogClient = mock(Gb28181CatalogClient.class);
    private final Gb28181CatalogSyncService service = new Gb28181CatalogSyncService(
            dao, accessConfigService, cameraService, catalogClient);

    private static Gb28181AccessConfigEntity entry(UUID id) {
        Gb28181AccessConfigEntity entity = new Gb28181AccessConfigEntity();
        entity.setId(id);
        entity.setEnabled(Boolean.TRUE);
        entity.setName("级联服务器");
        entity.setSipId("34020000002000000001");
        entity.setSipIp("192.168.1.10");
        entity.setSipPort("5060");
        entity.setUsername("admin");
        entity.setPassword("pw");
        entity.setCreatedAt(OffsetDateTime.now());
        entity.setUpdatedAt(OffsetDateTime.now());
        return entity;
    }

    private static Gb28181Config localConfig() {
        return new Gb28181Config(true, "34020000002000000099", "34020000", "192.168.1.100",
                "5060", "local-pw", null, null, null);
    }

    private void stubReachableEntry(UUID id) {
        when(dao.selectById(id)).thenReturn(entry(id));
        when(accessConfigService.get()).thenReturn(new AccessConfigResponse(localConfig(), null));
    }

    private static CameraResponse camera(UUID id, String gbCode) {
        return new CameraResponse(
                id, "本地-" + gbCode, null, "live", "s-" + gbCode, null, null, "办公楼",
                "RUNNING", "ONLINE", null, OffsetDateTime.now(), OffsetDateTime.now(),
                null, null, null, null, "GB28181", null, null, null,
                null, null, null, null, false, true, false, false, false, false, false, null, null,
                null, null, null, null, null, gbCode, null);
    }

    private static CloudDeviceItem cloudDevice(String name, String gbCode) {
        return new CloudDeviceItem(name, null, "GB28181", null, null, null, null, null, gbCode);
    }

    // --- diffByGbCode ---

    @Test
    void diffByGbCodeMarksNewAndUpdate() {
        UUID existing = UUID.randomUUID();

        List<CloudDeviceItem> items = Gb28181CatalogSyncService.diffByGbCode(
                List.of(cloudDevice("云端-北门", "34020000001320000101"),
                        cloudDevice("云端-东门", "34020000001320000102")),
                List.of(camera(existing, "34020000001320000101")));

        assertEquals("update", items.get(0).status());
        assertEquals(existing, items.get(0).localCameraId());
        assertEquals("new", items.get(1).status());
        assertNull(items.get(1).localCameraId());
    }

    @Test
    void diffByGbCodeIgnoresLocalCamerasWithoutGbCode() {
        List<CloudDeviceItem> items = Gb28181CatalogSyncService.diffByGbCode(
                List.of(cloudDevice("云端-北门", "34020000001320000101")),
                List.of(camera(UUID.randomUUID(), null)));

        assertEquals("new", items.get(0).status());
    }

    @Test
    void diffByGbCodeSkipsCloudDevicesWithoutDeviceId() {
        List<CloudDeviceItem> items = Gb28181CatalogSyncService.diffByGbCode(
                List.of(cloudDevice("云端-北门", null), cloudDevice("云端-东门", "  "),
                        cloudDevice("云端-西门", "34020000001320000103")),
                List.of());

        assertEquals(1, items.size());
        assertEquals("34020000001320000103", items.get(0).gbCode());
    }

    // --- precheck ---

    @Test
    void precheckThrowsNotFoundWhenEntryMissing() {
        UUID id = UUID.randomUUID();
        when(dao.selectById(id)).thenReturn(null);

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> service.precheck(id));
        assertEquals(HttpStatus.NOT_FOUND, exception.getStatusCode());
    }

    @Test
    void precheckThrowsBadRequestWhenEntrySipIdMissing() {
        UUID id = UUID.randomUUID();
        Gb28181AccessConfigEntity entity = entry(id);
        entity.setSipId(null);
        when(dao.selectById(id)).thenReturn(entity);

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> service.precheck(id));
        assertEquals(HttpStatus.BAD_REQUEST, exception.getStatusCode());
        assertTrue(exception.getReason().contains("SIP ID"));
    }

    @Test
    void precheckThrowsBadRequestWhenLocalConfigMissing() {
        UUID id = UUID.randomUUID();
        when(dao.selectById(id)).thenReturn(entry(id));
        when(accessConfigService.get()).thenReturn(new AccessConfigResponse(null, null));

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> service.precheck(id));
        assertEquals(HttpStatus.BAD_REQUEST, exception.getStatusCode());
    }

    @Test
    void precheckMapsCatalogToItemsWithDiffStatus() {
        UUID id = UUID.randomUUID();
        stubReachableEntry(id);
        UUID existing = UUID.randomUUID();
        when(cameraService.list()).thenReturn(List.of(camera(existing, "34020000001320000101")));
        when(catalogClient.queryCatalog(any(LocalSipConfig.class), any(TargetServer.class)))
                .thenReturn(List.of(
                        new Gb28181CatalogDevice("34020000001320000101", "北门摄像头", null, null, null, null),
                        new Gb28181CatalogDevice("34020000001320000102", null, null, null, null, null)));

        CloudSyncPrecheckResponse response = service.precheck(id);

        assertEquals(1, response.newCount());
        assertEquals(1, response.updateCount());
        CloudDeviceItem first = response.items().get(0);
        assertEquals("update", first.status());
        assertEquals(existing, first.localCameraId());
        assertEquals("GB28181", first.protocol());
        assertNull(first.sourceUrl());
        assertEquals("34020000001320000101", first.gbCode());
        // Name 为空时回退为 deviceId
        assertEquals("34020000001320000102", response.items().get(1).name());
    }

    @Test
    void precheckWrapsCatalogFailureAsBadGateway() {
        UUID id = UUID.randomUUID();
        stubReachableEntry(id);
        when(catalogClient.queryCatalog(any(), any()))
                .thenThrow(new Gb28181CatalogClient.CatalogQueryException("查询设备目录超时：级联服务器无响应"));

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> service.precheck(id));
        assertEquals(HttpStatus.BAD_GATEWAY, exception.getStatusCode());
        assertTrue(exception.getReason().contains("超时"));
    }

    // --- sync ---

    @Test
    void syncCreatesGbCameraWithoutSourceUrl() {
        UUID id = UUID.randomUUID();
        when(dao.selectById(id)).thenReturn(entry(id));
        when(cameraService.list()).thenReturn(List.of());

        CloudSyncResultResponse result = service.sync(id, new CloudSyncRequest(
                List.of(cloudDevice("云端-北门", "34020000001320000101")),
                "园区总部",
                false));

        assertEquals(1, result.created());
        ArgumentCaptor<CameraCreateRequest> captor = ArgumentCaptor.forClass(CameraCreateRequest.class);
        verify(cameraService).create(captor.capture());
        CameraCreateRequest created = captor.getValue();
        assertEquals("云端-北门", created.name());
        assertNull(created.sourceUrl());
        assertEquals("GB28181", created.protocol());
        assertEquals("34020000001320000101", created.gbCode());
        assertEquals("园区总部", created.area());
        assertNull(created.cloudPlatformId());
    }

    @Test
    void syncUpdatesOnlyNameAreaGbCodeWhenOverwrite() {
        UUID id = UUID.randomUUID();
        UUID localId = UUID.randomUUID();
        when(dao.selectById(id)).thenReturn(entry(id));
        when(cameraService.list()).thenReturn(List.of(camera(localId, "34020000001320000101")));

        CloudSyncResultResponse result = service.sync(id, new CloudSyncRequest(
                List.of(cloudDevice("云端-北门-新名", "34020000001320000101")),
                null,
                true));

        assertEquals(1, result.updated());
        ArgumentCaptor<CameraUpdateRequest> captor = ArgumentCaptor.forClass(CameraUpdateRequest.class);
        verify(cameraService).update(eq(localId), captor.capture());
        CameraUpdateRequest update = captor.getValue();
        assertEquals("云端-北门-新名", update.name());
        assertNull(update.sourceUrl());
        assertEquals("34020000001320000101", update.gbCode());
        verify(cameraService, never()).create(any());
    }

    @Test
    void syncSkipsExistingWhenNotOverwriteAndItemsWithoutGbCode() {
        UUID id = UUID.randomUUID();
        when(dao.selectById(id)).thenReturn(entry(id));
        when(cameraService.list()).thenReturn(List.of(camera(UUID.randomUUID(), "34020000001320000101")));

        CloudSyncResultResponse result = service.sync(id, new CloudSyncRequest(
                List.of(cloudDevice("云端-北门", "34020000001320000101"), cloudDevice("云端-无编码", null)),
                null,
                false));

        assertEquals(0, result.created());
        assertEquals(0, result.updated());
        assertEquals(2, result.skipped());
        verify(cameraService, never()).create(any());
        verify(cameraService, never()).update(any(), any());
    }

    @Test
    void syncThrowsNotFoundWhenEntryMissing() {
        UUID id = UUID.randomUUID();
        when(dao.selectById(id)).thenReturn(null);

        assertThrows(ResponseStatusException.class,
                () -> service.sync(id, new CloudSyncRequest(List.of(), null, false)));
    }
}
