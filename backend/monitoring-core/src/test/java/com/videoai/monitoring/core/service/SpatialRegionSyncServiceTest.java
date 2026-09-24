package com.videoai.monitoring.core.service;

import com.videoai.monitoring.common.vo.SpatialRegionSyncResponse;
import com.videoai.monitoring.core.client.SpatialBaseUrlHolder;
import com.videoai.monitoring.core.client.SpatialInfoFeign;
import com.videoai.monitoring.core.client.SpatialInfoFeignConfig;
import com.videoai.monitoring.core.client.SpatialInfoNode;
import com.videoai.monitoring.core.client.SpatialInfoTreeResponse;
import com.videoai.monitoring.core.dao.RegionDao;
import com.videoai.monitoring.core.entity.RegionEntity;
import com.videoai.monitoring.core.service.impl.SpatialRegionSyncServiceImpl;
import feign.RequestInterceptor;
import feign.RequestTemplate;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 空间区域同步：只新增、已有不动；接口不可访问只记日志不报错；基址取界面配置。
 */
class SpatialRegionSyncServiceTest {

    private static final String BASE_URL = "http://172.17.2.131:8080";

    private final SpatialInfoFeign spatialInfoFeign = mock(SpatialInfoFeign.class);
    private final SpatialConfigService spatialConfigService = mock(SpatialConfigService.class);
    private final RegionDao regionDao = mock(RegionDao.class);
    private final SpatialRegionSyncService service =
            new SpatialRegionSyncServiceImpl(spatialInfoFeign, spatialConfigService, regionDao);

    @BeforeEach
    void setUp() {
        when(spatialConfigService.resolveBaseUrl()).thenReturn(BASE_URL);
    }

    private static RegionEntity entity(UUID id, String name, UUID parentId, int sortOrder) {
        RegionEntity entity = new RegionEntity();
        entity.setId(id);
        entity.setName(name);
        entity.setParentId(parentId);
        entity.setSortOrder(sortOrder);
        entity.setCreatedAt(OffsetDateTime.now());
        entity.setUpdatedAt(OffsetDateTime.now());
        return entity;
    }

    private static SpatialInfoNode node(String id, String name, SpatialInfoNode... children) {
        return new SpatialInfoNode(id, name, null, null, 0, "DISTRICT", List.of(children));
    }

    private static SpatialInfoTreeResponse ok(SpatialInfoNode... roots) {
        return new SpatialInfoTreeResponse(true, "操作成功", "00000", List.of(roots));
    }

    @Test
    void syncOnlyCreatesMissingNodesAndReusesExistingOnes() {
        UUID parkId = UUID.randomUUID();
        UUID areaId = UUID.randomUUID();
        when(regionDao.selectAll()).thenReturn(List.of(
                entity(parkId, "团结湖数字经济产业园", null, 0),
                entity(areaId, "智能制造A", parkId, 0)));
        when(regionDao.maxSortOrder(areaId)).thenReturn(2);
        when(spatialInfoFeign.tree(anyBoolean())).thenReturn(ok(
                node("s-park", "团结湖数字经济产业园",
                        node("s-area", "智能制造A",
                                node("s-a1", "A1")))));

        SpatialRegionSyncResponse response = service.sync();

        assertTrue(response.success());
        assertEquals(1, response.created());
        assertEquals(2, response.skipped());
        assertEquals(3, response.total());
        ArgumentCaptor<RegionEntity> captor = ArgumentCaptor.forClass(RegionEntity.class);
        verify(regionDao, times(1)).insert(captor.capture());
        assertEquals("A1", captor.getValue().getName());
        assertEquals(areaId, captor.getValue().getParentId());
        assertEquals(3, captor.getValue().getSortOrder());
        // 已存在的两个节点不做任何更新
        verify(regionDao, never()).updateRegion(any());
    }

    @Test
    void syncCreatesSameNamedNodeUnderDifferentParentWithoutMerging() {
        UUID parkId = UUID.randomUUID();
        UUID rootA1Id = UUID.randomUUID();
        when(regionDao.selectAll()).thenReturn(List.of(
                entity(parkId, "团结湖数字经济产业园", null, 0),
                entity(rootA1Id, "A1", parkId, 0)));
        when(spatialInfoFeign.tree(anyBoolean())).thenReturn(ok(
                node("s-park", "团结湖数字经济产业园",
                        node("s-area", "智能制造A",
                                node("s-a1", "A1")))));

        SpatialRegionSyncResponse response = service.sync();

        assertTrue(response.success());
        assertEquals(2, response.created());
        assertEquals(1, response.skipped());
        ArgumentCaptor<RegionEntity> captor = ArgumentCaptor.forClass(RegionEntity.class);
        verify(regionDao, times(2)).insert(captor.capture());
        List<RegionEntity> inserted = captor.getAllValues();
        assertEquals("智能制造A", inserted.get(0).getName());
        assertEquals(parkId, inserted.get(0).getParentId());
        // A1 挂到新建的「智能制造A」下，而不是复用挂在其它的已有 A1
        assertEquals("A1", inserted.get(1).getName());
        assertEquals(inserted.get(0).getId(), inserted.get(1).getParentId());
        verify(regionDao, never()).updateRegion(any());
    }

    @Test
    void syncLogsAndReturnsFailureWhenServiceUnreachable() {
        when(spatialInfoFeign.tree(anyBoolean())).thenThrow(new RuntimeException("connect timed out"));

        SpatialRegionSyncResponse response = service.sync();

        assertFalse(response.success());
        assertEquals(0, response.created());
        assertEquals(0, response.skipped());
        assertEquals(0, response.total());
        assertTrue(response.message().contains("不可访问"));
        verify(regionDao, never()).insert(any(RegionEntity.class));
        verify(regionDao, never()).updateRegion(any());
        verify(regionDao, never()).selectAll();
        // 调用结束必须清理线程基址，避免线程复用串地址
        assertNull(SpatialBaseUrlHolder.get());
    }

    @Test
    void syncReturnsFailureWhenNoBaseUrlConfigured() {
        when(spatialConfigService.resolveBaseUrl()).thenReturn(null);

        SpatialRegionSyncResponse response = service.sync();

        assertFalse(response.success());
        assertEquals(0, response.created());
        assertTrue(response.message().contains("未配置"));
        verify(spatialInfoFeign, never()).tree(anyBoolean());
        verify(regionDao, never()).insert(any(RegionEntity.class));
    }

    @Test
    void syncReturnsFailureWhenUpstreamReportsError() {
        when(spatialInfoFeign.tree(anyBoolean()))
                .thenReturn(new SpatialInfoTreeResponse(false, "缺少必填参数: hasOther", "00003", null));

        SpatialRegionSyncResponse response = service.sync();

        assertFalse(response.success());
        assertEquals(0, response.created());
        assertTrue(response.message().contains("缺少必填参数"));
        verify(regionDao, never()).insert(any(RegionEntity.class));
    }

    @Test
    void syncWithoutSpatialNodesCreatesNothing() {
        when(spatialInfoFeign.tree(anyBoolean())).thenReturn(ok());
        when(regionDao.selectAll()).thenReturn(List.of());

        SpatialRegionSyncResponse response = service.sync();

        assertTrue(response.success());
        assertEquals(0, response.created());
        assertEquals(0, response.skipped());
        verify(regionDao, never()).insert(any(RegionEntity.class));
    }

    @Test
    void syncSkipsNodesWithoutNameButKeepsChildrenUnderCurrentParent() {
        UUID parkId = UUID.randomUUID();
        when(regionDao.selectAll()).thenReturn(List.of(entity(parkId, "园区", null, 0)));
        when(spatialInfoFeign.tree(anyBoolean())).thenReturn(ok(
                node("s-park", "园区",
                        node("s-blank", "  ",
                                node("s-a", "A")))));

        SpatialRegionSyncResponse response = service.sync();

        assertTrue(response.success());
        assertEquals(1, response.created());
        assertEquals(1, response.skipped());
        ArgumentCaptor<RegionEntity> captor = ArgumentCaptor.forClass(RegionEntity.class);
        verify(regionDao).insert(captor.capture());
        assertEquals("A", captor.getValue().getName());
        assertEquals(parkId, captor.getValue().getParentId());
    }

    @Test
    void interceptorOverridesFeignTargetWithConfiguredBaseUrl() {
        RequestInterceptor interceptor = new SpatialInfoFeignConfig().spatialInfoTargetInterceptor();

        // 未设置配置时保持 @FeignClient 的占位地址
        RequestTemplate placeholder = new RequestTemplate().method("GET").uri("/spatialServer/spatialInfo/tree");
        interceptor.apply(placeholder);
        assertFalse(placeholder.url().startsWith(BASE_URL));

        SpatialBaseUrlHolder.set(BASE_URL);
        try {
            RequestTemplate configured = new RequestTemplate().method("GET").uri("/spatialServer/spatialInfo/tree");
            interceptor.apply(configured);
            assertTrue(configured.url().startsWith(BASE_URL + "/spatialServer/spatialInfo/tree"),
                    "实际地址=" + configured.url());
        } finally {
            SpatialBaseUrlHolder.clear();
        }
    }
}
