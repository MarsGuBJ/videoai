package com.videoai.monitoring.core.service;

import com.videoai.monitoring.common.dto.RegionCreateRequest;
import com.videoai.monitoring.common.dto.RegionReorderRequest;
import com.videoai.monitoring.common.dto.RegionUpdateRequest;
import com.videoai.monitoring.common.vo.RegionNodeResponse;
import com.videoai.monitoring.core.dao.CameraDao;
import com.videoai.monitoring.core.dao.RegionDao;
import com.videoai.monitoring.core.entity.RegionEntity;
import com.videoai.monitoring.core.service.impl.RegionServiceImpl;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.nullable;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class RegionServiceTest {

    private final RegionDao regionDao = mock(RegionDao.class);
    private final CameraDao cameraDao = mock(CameraDao.class);
    private final RegionService service = new RegionServiceImpl(regionDao, cameraDao);

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

    @Test
    void createAssignsMaxSortOrderPlusOne() {
        UUID parentId = UUID.randomUUID();
        when(regionDao.selectById(parentId)).thenReturn(entity(parentId, "东区", null, 0));
        when(regionDao.selectByParentAndName(parentId, "一车间")).thenReturn(List.of());
        when(regionDao.maxSortOrder(parentId)).thenReturn(2);

        RegionNodeResponse response = service.create(new RegionCreateRequest(" 一车间 ", parentId));

        assertEquals("一车间", response.name());
        assertEquals(parentId, response.parentId());
        assertEquals(3, response.sortOrder());
        assertEquals(0, response.deviceCount());
        assertTrue(response.children().isEmpty());
        ArgumentCaptor<RegionEntity> captor = ArgumentCaptor.forClass(RegionEntity.class);
        verify(regionDao).insert(captor.capture());
        assertEquals(3, captor.getValue().getSortOrder());
        assertEquals("一车间", captor.getValue().getName());
    }

    @Test
    void createDefaultsSortOrderToZeroWhenNoSiblings() {
        when(regionDao.selectByParentAndName(null, "东区")).thenReturn(List.of());
        when(regionDao.maxSortOrder(null)).thenReturn(null);

        RegionNodeResponse response = service.create(new RegionCreateRequest("东区", null));

        assertEquals(0, response.sortOrder());
    }

    @Test
    void createThrowsNotFoundWhenParentMissing() {
        UUID parentId = UUID.randomUUID();
        when(regionDao.selectById(parentId)).thenReturn(null);

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> service.create(new RegionCreateRequest("一车间", parentId)));

        assertEquals(HttpStatus.NOT_FOUND, exception.getStatusCode());
        verify(regionDao, never()).insert(any(RegionEntity.class));
    }

    @Test
    void createThrowsConflictWhenSiblingNameExists() {
        UUID parentId = UUID.randomUUID();
        when(regionDao.selectById(parentId)).thenReturn(entity(parentId, "东区", null, 0));
        when(regionDao.selectByParentAndName(parentId, "一车间"))
                .thenReturn(List.of(entity(UUID.randomUUID(), "一车间", parentId, 0)));

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> service.create(new RegionCreateRequest("一车间", parentId)));

        assertEquals(HttpStatus.CONFLICT, exception.getStatusCode());
        assertEquals("同级区域名称已存在", exception.getReason());
        verify(regionDao, never()).insert(any(RegionEntity.class));
    }

    @Test
    void renameRewritesCameraAreaPrefix() {
        UUID parentId = UUID.randomUUID();
        UUID childId = UUID.randomUUID();
        RegionEntity parent = entity(parentId, "东区", null, 0);
        RegionEntity child = entity(childId, "一车间", parentId, 1);
        when(regionDao.selectById(childId)).thenReturn(child);
        when(regionDao.selectById(parentId)).thenReturn(parent);
        when(regionDao.selectByParentAndName(parentId, "二车间")).thenReturn(List.of());
        when(cameraDao.selectAreaCounts())
                .thenReturn(List.of(Map.<String, Object>of("area", "东区 / 二车间", "cnt", 5L)));

        RegionNodeResponse response = service.rename(childId, new RegionUpdateRequest("二车间"));

        ArgumentCaptor<RegionEntity> captor = ArgumentCaptor.forClass(RegionEntity.class);
        verify(regionDao).updateRegion(captor.capture());
        assertEquals("二车间", captor.getValue().getName());
        verify(cameraDao).replaceAreaPrefix("东区 / 一车间", "东区 / 二车间");
        assertEquals("二车间", response.name());
        assertEquals(5, response.deviceCount());
    }

    @Test
    void renameThrowsNotFoundWhenMissing() {
        UUID id = UUID.randomUUID();
        when(regionDao.selectById(id)).thenReturn(null);

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> service.rename(id, new RegionUpdateRequest("二车间")));

        assertEquals(HttpStatus.NOT_FOUND, exception.getStatusCode());
        verify(cameraDao, never()).replaceAreaPrefix(any(), any());
    }

    @Test
    void renameThrowsConflictWhenSiblingNameExists() {
        UUID parentId = UUID.randomUUID();
        UUID childId = UUID.randomUUID();
        when(regionDao.selectById(childId)).thenReturn(entity(childId, "一车间", parentId, 1));
        when(regionDao.selectByParentAndName(parentId, "二车间"))
                .thenReturn(List.of(entity(UUID.randomUUID(), "二车间", parentId, 0)));

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> service.rename(childId, new RegionUpdateRequest("二车间")));

        assertEquals(HttpStatus.CONFLICT, exception.getStatusCode());
        verify(regionDao, never()).updateRegion(any());
        verify(cameraDao, never()).replaceAreaPrefix(any(), any());
    }

    @Test
    void reorderThrowsBadRequestWhenIdSetMismatch() {
        UUID parentId = UUID.randomUUID();
        UUID a = UUID.randomUUID();
        UUID b = UUID.randomUUID();
        when(regionDao.selectAll()).thenReturn(List.of(
                entity(a, "一车间", parentId, 0),
                entity(b, "二车间", parentId, 1)));

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> service.reorder(new RegionReorderRequest(parentId, List.of(a, UUID.randomUUID()))));

        assertEquals(HttpStatus.BAD_REQUEST, exception.getStatusCode());
        verify(regionDao, never()).updateRegion(any());
    }

    @Test
    void reorderWritesSortOrdersByIndex() {
        UUID parentId = UUID.randomUUID();
        UUID a = UUID.randomUUID();
        UUID b = UUID.randomUUID();
        when(regionDao.selectAll()).thenReturn(List.of(
                entity(a, "一车间", parentId, 0),
                entity(b, "二车间", parentId, 1)));

        service.reorder(new RegionReorderRequest(parentId, List.of(b, a)));

        ArgumentCaptor<RegionEntity> captor = ArgumentCaptor.forClass(RegionEntity.class);
        verify(regionDao, times(2)).updateRegion(captor.capture());
        List<RegionEntity> updates = captor.getAllValues();
        assertEquals(b, updates.get(0).getId());
        assertEquals(0, updates.get(0).getSortOrder());
        assertEquals(a, updates.get(1).getId());
        assertEquals(1, updates.get(1).getSortOrder());
    }

    @Test
    void deleteThrowsConflictWhenChildrenExist() {
        UUID id = UUID.randomUUID();
        RegionEntity node = entity(id, "东区", null, 0);
        when(regionDao.selectById(id)).thenReturn(node);
        when(regionDao.selectAll()).thenReturn(List.of(node, entity(UUID.randomUUID(), "一车间", id, 0)));

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> service.delete(id));

        assertEquals(HttpStatus.CONFLICT, exception.getStatusCode());
        assertEquals("请先删除子区域", exception.getReason());
        verify(regionDao, never()).deleteById(any(UUID.class));
    }

    @Test
    void deleteThrowsConflictWhenAreaOccupied() {
        UUID id = UUID.randomUUID();
        RegionEntity node = entity(id, "东区", null, 0);
        when(regionDao.selectById(id)).thenReturn(node);
        when(regionDao.selectAll()).thenReturn(List.of(node));
        when(cameraDao.countByAreaPrefix("东区")).thenReturn(2);

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> service.delete(id));

        assertEquals(HttpStatus.CONFLICT, exception.getStatusCode());
        verify(regionDao, never()).deleteById(any(UUID.class));
    }

    @Test
    void deleteRemovesWhenEmpty() {
        UUID id = UUID.randomUUID();
        RegionEntity node = entity(id, "东区", null, 0);
        when(regionDao.selectById(id)).thenReturn(node);
        when(regionDao.selectAll()).thenReturn(List.of(node));
        when(cameraDao.countByAreaPrefix("东区")).thenReturn(0);

        service.delete(id);

        verify(regionDao).deleteById(id);
    }

    @Test
    void treeSyncsCameraAreasIntoNestedSortedNodes() {
        when(regionDao.selectAll()).thenReturn(List.of());
        when(regionDao.maxSortOrder(nullable(UUID.class))).thenReturn(null);
        when(cameraDao.selectDistinctAreas()).thenReturn(List.of("东区 / 一车间"));
        when(cameraDao.selectAreaCounts())
                .thenReturn(List.of(Map.<String, Object>of("area", "东区 / 一车间", "cnt", 3L)));

        List<RegionNodeResponse> tree = service.tree();

        verify(regionDao, times(2)).insert(any(RegionEntity.class));
        assertEquals(1, tree.size());
        RegionNodeResponse root = tree.get(0);
        assertEquals("东区", root.name());
        assertEquals(0, root.sortOrder());
        assertEquals(0, root.deviceCount());
        assertEquals(1, root.children().size());
        RegionNodeResponse child = root.children().get(0);
        assertEquals("一车间", child.name());
        assertEquals(root.id(), child.parentId());
        assertEquals(3, child.deviceCount());
        assertTrue(child.children().isEmpty());
    }

    @Test
    void treeCountsUnspacedAreaVariantsTowardNormalizedNode() {
        // 历史数据分隔符不带空格（东区/一车间）时，设备计数仍应归并到规范化节点
        when(regionDao.selectAll()).thenReturn(List.of());
        when(regionDao.maxSortOrder(nullable(UUID.class))).thenReturn(null);
        when(cameraDao.selectDistinctAreas()).thenReturn(List.of("东区/一车间"));
        when(cameraDao.selectAreaCounts()).thenReturn(List.of(
                Map.<String, Object>of("area", "东区/一车间", "cnt", 3L),
                Map.<String, Object>of("area", "东区 / 一车间", "cnt", 2L)));

        List<RegionNodeResponse> tree = service.tree();

        assertEquals(1, tree.size());
        RegionNodeResponse child = tree.get(0).children().get(0);
        assertEquals("一车间", child.name());
        assertEquals(5, child.deviceCount());
    }

    @Test
    void treeSortsSiblingsBySortOrder() {
        UUID a = UUID.randomUUID();
        UUID b = UUID.randomUUID();
        when(regionDao.selectAll()).thenReturn(List.of(
                entity(a, "西区", null, 1),
                entity(b, "东区", null, 0)));
        when(cameraDao.selectDistinctAreas()).thenReturn(List.of());
        when(cameraDao.selectAreaCounts()).thenReturn(List.of());

        List<RegionNodeResponse> tree = service.tree();

        assertEquals(List.of("东区", "西区"), tree.stream().map(RegionNodeResponse::name).toList());
        verify(regionDao, never()).insert(any(RegionEntity.class));
    }
}
