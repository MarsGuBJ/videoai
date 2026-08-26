package com.videoai.monitoring.core.service;

import com.videoai.monitoring.common.dto.CloudPlatformCreateRequest;
import com.videoai.monitoring.common.dto.CloudPlatformUpdateRequest;
import com.videoai.monitoring.common.vo.CloudPlatformResponse;
import com.videoai.monitoring.core.dao.CloudPlatformDao;
import com.videoai.monitoring.core.entity.CloudPlatformEntity;
import com.videoai.monitoring.core.service.impl.CloudPlatformServiceImpl;
import org.junit.jupiter.api.Test;
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

class CloudPlatformServiceTest {

    private final CloudPlatformDao dao = mock(CloudPlatformDao.class);
    private final CloudPlatformService service = new CloudPlatformServiceImpl(dao);

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
}
