package com.videoai.monitoring.core.service;

import com.videoai.monitoring.common.dto.SpatialConfigUpdateRequest;
import com.videoai.monitoring.common.vo.SpatialConfigResponse;
import com.videoai.monitoring.core.dao.SpatialConfigDao;
import com.videoai.monitoring.core.entity.SpatialConfigEntity;
import com.videoai.monitoring.core.service.impl.SpatialConfigServiceImpl;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.time.OffsetDateTime;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 空间服务基址配置：读写落库、失败回退 yml 默认值、地址校验。
 */
class SpatialConfigServiceTest {

    private static final String FALLBACK = "http://fallback:8080";

    private final SpatialConfigDao spatialConfigDao = mock(SpatialConfigDao.class);
    private final SpatialConfigService service = new SpatialConfigServiceImpl(spatialConfigDao, FALLBACK);

    private static SpatialConfigEntity row(String baseUrl) {
        SpatialConfigEntity entity = new SpatialConfigEntity();
        entity.setId(SpatialConfigEntity.SINGLETON_ID);
        entity.setBaseUrl(baseUrl);
        entity.setUpdatedAt(OffsetDateTime.now());
        return entity;
    }

    @Test
    void getReturnsStoredBaseUrl() {
        when(spatialConfigDao.selectById(SpatialConfigEntity.SINGLETON_ID)).thenReturn(row("http://172.17.2.131:8080"));

        SpatialConfigResponse response = service.get();

        assertEquals("http://172.17.2.131:8080", response.baseUrl());
    }

    @Test
    void getFallsBackToYmlDefaultWhenRowMissing() {
        when(spatialConfigDao.selectById(SpatialConfigEntity.SINGLETON_ID)).thenReturn(null);

        SpatialConfigResponse response = service.get();

        assertEquals(FALLBACK, response.baseUrl());
        assertNull(response.updatedAt());
    }

    @Test
    void resolveBaseUrlPrefersStoredValue() {
        when(spatialConfigDao.selectById(SpatialConfigEntity.SINGLETON_ID)).thenReturn(row("http://stored:9000/"));

        assertEquals("http://stored:9000", service.resolveBaseUrl());
    }

    @Test
    void resolveBaseUrlFallsBackWhenStoredValueBlank() {
        when(spatialConfigDao.selectById(SpatialConfigEntity.SINGLETON_ID)).thenReturn(row("   "));

        assertEquals(FALLBACK, service.resolveBaseUrl());
    }

    @Test
    void saveNormalizesTrailingSlashAndUpdatesExistingRow() {
        when(spatialConfigDao.updateById(any(SpatialConfigEntity.class))).thenReturn(1);

        SpatialConfigResponse response = service.save(new SpatialConfigUpdateRequest("  http://10.0.0.9:8080/  "));

        assertEquals("http://10.0.0.9:8080", response.baseUrl());
        ArgumentCaptor<SpatialConfigEntity> captor = ArgumentCaptor.forClass(SpatialConfigEntity.class);
        verify(spatialConfigDao).updateById(captor.capture());
        assertEquals(SpatialConfigEntity.SINGLETON_ID, captor.getValue().getId());
        assertEquals("http://10.0.0.9:8080", captor.getValue().getBaseUrl());
        verify(spatialConfigDao, never()).insert(any(SpatialConfigEntity.class));
    }

    @Test
    void saveInsertsRowWhenMissing() {
        when(spatialConfigDao.updateById(any(SpatialConfigEntity.class))).thenReturn(0);

        SpatialConfigResponse response = service.save(new SpatialConfigUpdateRequest("https://spatial.example.com"));

        assertEquals("https://spatial.example.com", response.baseUrl());
        verify(spatialConfigDao).insert(any(SpatialConfigEntity.class));
    }

    @Test
    void saveRejectsRelativeUrl() {
        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> service.save(new SpatialConfigUpdateRequest("172.17.2.131:8080")));

        assertEquals(HttpStatus.BAD_REQUEST, exception.getStatusCode());
        verify(spatialConfigDao, never()).updateById(any(SpatialConfigEntity.class));
        verify(spatialConfigDao, never()).insert(any(SpatialConfigEntity.class));
    }

    @Test
    void saveRejectsBlankUrl() {
        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> service.save(new SpatialConfigUpdateRequest("   ")));

        assertEquals(HttpStatus.BAD_REQUEST, exception.getStatusCode());
        verify(spatialConfigDao, never()).updateById(any(SpatialConfigEntity.class));
    }
}
