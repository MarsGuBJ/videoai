package com.videoai.monitoring.core.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.videoai.monitoring.common.dto.CertificateCreateRequest;
import com.videoai.monitoring.common.dto.Ga1400Config;
import com.videoai.monitoring.common.dto.Ga1400EntryRequest;
import com.videoai.monitoring.common.dto.Gb28181Config;
import com.videoai.monitoring.common.dto.Gb28181EntryRequest;
import com.videoai.monitoring.common.vo.Ga1400EntryResponse;
import com.videoai.monitoring.common.vo.Gb28181EntryResponse;
import com.videoai.monitoring.core.dao.AccessConfigDao;
import com.videoai.monitoring.core.dao.DeviceCertificateDao;
import com.videoai.monitoring.core.dao.Ga1400AccessConfigDao;
import com.videoai.monitoring.core.dao.Gb28181AccessConfigDao;
import com.videoai.monitoring.core.entity.Ga1400AccessConfigEntity;
import com.videoai.monitoring.core.entity.Gb28181AccessConfigEntity;
import com.videoai.monitoring.core.service.impl.AccessConfigServiceImpl;
import org.junit.jupiter.api.Test;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AccessConfigServiceTest {

    private static Gb28181Config validGb28181() {
        return new Gb28181Config(
                true,
                "34020000002000000001",
                "3402000000",
                "192.168.1.10",
                "5060",
                "12345678",
                "5061",
                "30000",
                "30100"
        );
    }

    private static Ga1400Config validGa1400() {
        return new Ga1400Config(
                true,
                "34020000002000000001",
                "192.168.1.20",
                "8080",
                "secret",
                "/viid",
                true
        );
    }

    private static Ga1400EntryRequest validGa1400Entry() {
        return new Ga1400EntryRequest(
                true,
                "34020000002000000001",
                "192.168.1.20",
                "8080",
                "secret",
                "/viid",
                true
        );
    }

    private static Gb28181EntryRequest validGb28181Entry() {
        return new Gb28181EntryRequest(
                true,
                "34020000002000000001",
                "3402000000",
                "192.168.1.10",
                "5060",
                "12345678",
                "5061",
                "30000",
                "30100"
        );
    }

    private static AccessConfigServiceImpl newService(Ga1400AccessConfigDao ga1400Dao) {
        return newService(ga1400Dao, mock(Gb28181AccessConfigDao.class));
    }

    private static AccessConfigServiceImpl newService(Ga1400AccessConfigDao ga1400Dao,
                                                      Gb28181AccessConfigDao gb28181Dao) {
        return new AccessConfigServiceImpl(
                mock(AccessConfigDao.class),
                mock(DeviceCertificateDao.class),
                ga1400Dao,
                gb28181Dao,
                new ObjectMapper()
        );
    }

    private static Ga1400AccessConfigEntity ga1400Entity(UUID id, Ga1400EntryRequest request) {
        Ga1400AccessConfigEntity entity = new Ga1400AccessConfigEntity();
        entity.setId(id);
        entity.setEnabled(request.enabled());
        entity.setPlatformId(request.platformId());
        entity.setPlatformIp(request.platformIp());
        entity.setPort(request.port());
        entity.setPassword(request.password());
        entity.setResourcePath(request.resourcePath());
        entity.setAutoRegister(request.autoRegister());
        entity.setCreatedAt(OffsetDateTime.now());
        entity.setUpdatedAt(OffsetDateTime.now());
        return entity;
    }

    @Test
    void validGb28181Passes() {
        assertDoesNotThrow(() -> AccessConfigService.validateGb28181(validGb28181()));
    }

    @Test
    void sipIdMustBe20Digits() {
        Gb28181Config shortId = new Gb28181Config(true, "12345", "3402000000",
                "192.168.1.10", "5060", "pw", "5061", "30000", "30100");
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateGb28181(shortId));

        Gb28181Config letters = new Gb28181Config(true, "3402000000200000000a", "3402000000",
                "192.168.1.10", "5060", "pw", "5061", "30000", "30100");
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateGb28181(letters));
    }

    @Test
    void sipDomainMustBe10Digits() {
        Gb28181Config config = new Gb28181Config(true, "34020000002000000001", "34020000",
                "192.168.1.10", "5060", "pw", "5061", "30000", "30100");
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateGb28181(config));
    }

    @Test
    void portOutOfRangeRejected() {
        Gb28181Config zero = new Gb28181Config(true, "34020000002000000001", "3402000000",
                "192.168.1.10", "0", "pw", "5061", "30000", "30100");
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateGb28181(zero));

        Gb28181Config tooBig = new Gb28181Config(true, "34020000002000000001", "3402000000",
                "192.168.1.10", "5060", "pw", "5061", "30100", "65536");
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateGb28181(tooBig));

        Gb28181Config notANumber = new Gb28181Config(true, "34020000002000000001", "3402000000",
                "192.168.1.10", "abc", "pw", "5061", "30000", "30100");
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateGb28181(notANumber));
    }

    @Test
    void receivePortStartMustNotExceedEnd() {
        Gb28181Config config = new Gb28181Config(true, "34020000002000000001", "3402000000",
                "192.168.1.10", "5060", "pw", "5061", "30100", "30000");
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateGb28181(config));

        Gb28181Config equal = new Gb28181Config(true, "34020000002000000001", "3402000000",
                "192.168.1.10", "5060", "pw", "5061", "30000", "30000");
        assertDoesNotThrow(() -> AccessConfigService.validateGb28181(equal));
    }

    @Test
    void validGa1400Passes() {
        assertDoesNotThrow(() -> AccessConfigService.validateGa1400(validGa1400()));
    }

    @Test
    void platformIdMustBe20Digits() {
        Ga1400Config config = new Ga1400Config(true, "123", "192.168.1.20", "8080", "s", "/viid", true);
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateGa1400(config));
    }

    @Test
    void ga1400PortOutOfRangeRejected() {
        Ga1400Config config = new Ga1400Config(true, "34020000002000000001", "192.168.1.20",
                "70000", "s", "/viid", true);
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateGa1400(config));
    }

    @Test
    void certificateValidation() {
        assertDoesNotThrow(() -> AccessConfigService.validateCertificate(
                new CertificateCreateRequest("34020000002000000001", "CERT-PEM", "单向")));
        assertDoesNotThrow(() -> AccessConfigService.validateCertificate(
                new CertificateCreateRequest("34020000002000000001", "CERT-PEM", "双向")));

        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateCertificate(
                new CertificateCreateRequest("123", "CERT-PEM", "单向")));
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateCertificate(
                new CertificateCreateRequest("34020000002000000001", "  ", "单向")));
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateCertificate(
                new CertificateCreateRequest("34020000002000000001", "CERT-PEM", "无")));
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateCertificate(
                new CertificateCreateRequest("34020000002000000001", "CERT-PEM", null)));
    }

    @Test
    void validGa1400EntryPasses() {
        assertDoesNotThrow(() -> AccessConfigService.validateGa1400Entry(validGa1400Entry()));
    }

    @Test
    void ga1400EntryNullRejected() {
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateGa1400Entry(null));
    }

    @Test
    void ga1400EntryPlatformIdMustBe20Digits() {
        Ga1400EntryRequest request = new Ga1400EntryRequest(true, "123", "192.168.1.20", "8080", "s", "/viid", true);
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateGa1400Entry(request));

        Ga1400EntryRequest letters = new Ga1400EntryRequest(true, "3402000000200000000a", "192.168.1.20",
                "8080", "s", "/viid", true);
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateGa1400Entry(letters));
    }

    @Test
    void ga1400EntryPortOutOfRangeRejected() {
        Ga1400EntryRequest zero = new Ga1400EntryRequest(true, "34020000002000000001", "192.168.1.20",
                "0", "s", "/viid", true);
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateGa1400Entry(zero));

        Ga1400EntryRequest tooBig = new Ga1400EntryRequest(true, "34020000002000000001", "192.168.1.20",
                "65536", "s", "/viid", true);
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateGa1400Entry(tooBig));

        Ga1400EntryRequest notANumber = new Ga1400EntryRequest(true, "34020000002000000001", "192.168.1.20",
                "abc", "s", "/viid", true);
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateGa1400Entry(notANumber));
    }

    @Test
    void listGa1400EntriesMapsEntities() {
        Ga1400AccessConfigDao dao = mock(Ga1400AccessConfigDao.class);
        Ga1400AccessConfigEntity entity = ga1400Entity(UUID.randomUUID(), validGa1400Entry());
        when(dao.selectAllOrdered()).thenReturn(List.of(entity));

        List<Ga1400EntryResponse> entries = newService(dao).listGa1400Entries();

        assertEquals(1, entries.size());
        Ga1400EntryResponse entry = entries.get(0);
        assertEquals(entity.getId(), entry.id());
        assertEquals(entity.getPlatformId(), entry.platformId());
        assertEquals(entity.getPlatformIp(), entry.platformIp());
        assertEquals(entity.getPort(), entry.port());
        assertEquals(entity.getCreatedAt(), entry.createdAt());
    }

    @Test
    void createGa1400EntryValidatesAndInserts() {
        Ga1400AccessConfigDao dao = mock(Ga1400AccessConfigDao.class);
        Ga1400EntryRequest request = validGa1400Entry();
        when(dao.selectById(any(UUID.class)))
                .thenAnswer(invocation -> ga1400Entity(invocation.getArgument(0), request));

        Ga1400EntryResponse created = newService(dao).createGa1400Entry(request);

        verify(dao).insert(any(Ga1400AccessConfigEntity.class));
        assertEquals("34020000002000000001", created.platformId());
        assertEquals("8080", created.port());
        assertEquals(true, created.enabled());
        assertEquals(true, created.autoRegister());
    }

    @Test
    void createGa1400EntryRejectsInvalidRequest() {
        Ga1400AccessConfigDao dao = mock(Ga1400AccessConfigDao.class);
        Ga1400EntryRequest request = new Ga1400EntryRequest(true, "bad", "192.168.1.20", "8080", "s", "/viid", true);

        assertThrows(IllegalArgumentException.class, () -> newService(dao).createGa1400Entry(request));
        verify(dao, never()).insert(any(Ga1400AccessConfigEntity.class));
    }

    @Test
    void updateGa1400EntryUpdatesExisting() {
        Ga1400AccessConfigDao dao = mock(Ga1400AccessConfigDao.class);
        UUID id = UUID.randomUUID();
        Ga1400EntryRequest stored = new Ga1400EntryRequest(true, "34020000002000000001", "192.168.1.20",
                "8080", "old", "/viid", false);
        Ga1400AccessConfigEntity entity = ga1400Entity(id, stored);
        when(dao.selectById(id)).thenReturn(entity);

        Ga1400EntryRequest request = new Ga1400EntryRequest(false, "34020000002000000002", "192.168.1.21",
                "9090", "new", "/viid2", true);
        Ga1400EntryResponse updated = newService(dao).updateGa1400Entry(id, request);

        verify(dao).updateById(any(Ga1400AccessConfigEntity.class));
        assertEquals("34020000002000000002", updated.platformId());
        assertEquals("9090", updated.port());
        assertEquals(false, updated.enabled());
    }

    @Test
    void updateGa1400EntryNotFoundRejected() {
        Ga1400AccessConfigDao dao = mock(Ga1400AccessConfigDao.class);
        UUID id = UUID.randomUUID();
        when(dao.selectById(id)).thenReturn(null);

        assertThrows(IllegalArgumentException.class, () -> newService(dao).updateGa1400Entry(id, validGa1400Entry()));
        verify(dao, never()).updateById(any(Ga1400AccessConfigEntity.class));
    }

    @Test
    void updateGa1400EntryRejectsInvalidRequest() {
        Ga1400AccessConfigDao dao = mock(Ga1400AccessConfigDao.class);
        Ga1400EntryRequest request = new Ga1400EntryRequest(true, "34020000002000000001", "192.168.1.20",
                "70000", "s", "/viid", true);

        assertThrows(IllegalArgumentException.class,
                () -> newService(dao).updateGa1400Entry(UUID.randomUUID(), request));
        verify(dao, never()).updateById(any(Ga1400AccessConfigEntity.class));
    }

    @Test
    void deleteGa1400EntryDelegatesToDao() {
        Ga1400AccessConfigDao dao = mock(Ga1400AccessConfigDao.class);
        UUID id = UUID.randomUUID();

        newService(dao).deleteGa1400Entry(id);

        verify(dao).deleteById(id);
    }

    private static Gb28181AccessConfigEntity gb28181Entity(UUID id, Gb28181EntryRequest request) {
        Gb28181AccessConfigEntity entity = new Gb28181AccessConfigEntity();
        entity.setId(id);
        entity.setEnabled(request.enabled());
        entity.setSipId(request.sipId());
        entity.setSipDomain(request.sipDomain());
        entity.setSipIp(request.sipIp());
        entity.setSipPort(request.sipPort());
        entity.setPassword(request.password());
        entity.setParentPort(request.parentPort());
        entity.setReceivePortStart(request.receivePortStart());
        entity.setReceivePortEnd(request.receivePortEnd());
        entity.setCreatedAt(OffsetDateTime.now());
        entity.setUpdatedAt(OffsetDateTime.now());
        return entity;
    }

    @Test
    void validGb28181EntryPasses() {
        assertDoesNotThrow(() -> AccessConfigService.validateGb28181Entry(validGb28181Entry()));
    }

    @Test
    void gb28181EntryNullRejected() {
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateGb28181Entry(null));
    }

    @Test
    void gb28181EntrySipIdMustBe20Digits() {
        Gb28181EntryRequest request = new Gb28181EntryRequest(true, "12345", "3402000000",
                "192.168.1.10", "5060", "pw", "5061", "30000", "30100");
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateGb28181Entry(request));

        Gb28181EntryRequest letters = new Gb28181EntryRequest(true, "3402000000200000000a", "3402000000",
                "192.168.1.10", "5060", "pw", "5061", "30000", "30100");
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateGb28181Entry(letters));
    }

    @Test
    void gb28181EntrySipDomainMustBe10Digits() {
        Gb28181EntryRequest request = new Gb28181EntryRequest(true, "34020000002000000001", "34020000",
                "192.168.1.10", "5060", "pw", "5061", "30000", "30100");
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateGb28181Entry(request));
    }

    @Test
    void gb28181EntryPortOutOfRangeRejected() {
        Gb28181EntryRequest zero = new Gb28181EntryRequest(true, "34020000002000000001", "3402000000",
                "192.168.1.10", "0", "pw", "5061", "30000", "30100");
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateGb28181Entry(zero));

        Gb28181EntryRequest tooBig = new Gb28181EntryRequest(true, "34020000002000000001", "3402000000",
                "192.168.1.10", "65536", "pw", "5061", "30000", "30100");
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateGb28181Entry(tooBig));

        Gb28181EntryRequest notANumber = new Gb28181EntryRequest(true, "34020000002000000001", "3402000000",
                "192.168.1.10", "abc", "pw", "5061", "30000", "30100");
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateGb28181Entry(notANumber));
    }

    @Test
    void gb28181EntryReceivePortRangeRejected() {
        Gb28181EntryRequest startAfterEnd = new Gb28181EntryRequest(true, "34020000002000000001", "3402000000",
                "192.168.1.10", "5060", "pw", "5061", "30100", "30000");
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateGb28181Entry(startAfterEnd));

        Gb28181EntryRequest outOfRange = new Gb28181EntryRequest(true, "34020000002000000001", "3402000000",
                "192.168.1.10", "5060", "pw", "5061", "30000", "65536");
        assertThrows(IllegalArgumentException.class, () -> AccessConfigService.validateGb28181Entry(outOfRange));

        Gb28181EntryRequest equal = new Gb28181EntryRequest(true, "34020000002000000001", "3402000000",
                "192.168.1.10", "5060", "pw", "5061", "30000", "30000");
        assertDoesNotThrow(() -> AccessConfigService.validateGb28181Entry(equal));
    }

    @Test
    void listGb28181EntriesMapsEntities() {
        Gb28181AccessConfigDao dao = mock(Gb28181AccessConfigDao.class);
        Gb28181AccessConfigEntity entity = gb28181Entity(UUID.randomUUID(), validGb28181Entry());
        when(dao.selectAllOrdered()).thenReturn(List.of(entity));

        List<Gb28181EntryResponse> entries = newService(mock(Ga1400AccessConfigDao.class), dao)
                .listGb28181Entries();

        assertEquals(1, entries.size());
        Gb28181EntryResponse entry = entries.get(0);
        assertEquals(entity.getId(), entry.id());
        assertEquals(entity.getSipId(), entry.sipId());
        assertEquals(entity.getSipDomain(), entry.sipDomain());
        assertEquals(entity.getSipPort(), entry.sipPort());
        assertEquals(entity.getCreatedAt(), entry.createdAt());
    }

    @Test
    void createGb28181EntryValidatesAndInserts() {
        Gb28181AccessConfigDao dao = mock(Gb28181AccessConfigDao.class);
        Gb28181EntryRequest request = validGb28181Entry();
        when(dao.selectById(any(UUID.class)))
                .thenAnswer(invocation -> gb28181Entity(invocation.getArgument(0), request));

        Gb28181EntryResponse created = newService(mock(Ga1400AccessConfigDao.class), dao)
                .createGb28181Entry(request);

        verify(dao).insert(any(Gb28181AccessConfigEntity.class));
        assertEquals("34020000002000000001", created.sipId());
        assertEquals("5060", created.sipPort());
        assertEquals(true, created.enabled());
        assertEquals("30100", created.receivePortEnd());
    }

    @Test
    void createGb28181EntryRejectsInvalidRequest() {
        Gb28181AccessConfigDao dao = mock(Gb28181AccessConfigDao.class);
        Gb28181EntryRequest request = new Gb28181EntryRequest(true, "bad", "3402000000",
                "192.168.1.10", "5060", "pw", "5061", "30000", "30100");

        assertThrows(IllegalArgumentException.class,
                () -> newService(mock(Ga1400AccessConfigDao.class), dao).createGb28181Entry(request));
        verify(dao, never()).insert(any(Gb28181AccessConfigEntity.class));
    }

    @Test
    void updateGb28181EntryUpdatesExisting() {
        Gb28181AccessConfigDao dao = mock(Gb28181AccessConfigDao.class);
        UUID id = UUID.randomUUID();
        Gb28181EntryRequest stored = new Gb28181EntryRequest(true, "34020000002000000001", "3402000000",
                "192.168.1.10", "5060", "old", "5061", "30000", "30100");
        Gb28181AccessConfigEntity entity = gb28181Entity(id, stored);
        when(dao.selectById(id)).thenReturn(entity);

        Gb28181EntryRequest request = new Gb28181EntryRequest(false, "34020000002000000002", "3402000001",
                "192.168.1.11", "5062", "new", "5063", "31000", "31100");
        Gb28181EntryResponse updated = newService(mock(Ga1400AccessConfigDao.class), dao)
                .updateGb28181Entry(id, request);

        verify(dao).updateById(any(Gb28181AccessConfigEntity.class));
        assertEquals("34020000002000000002", updated.sipId());
        assertEquals("5062", updated.sipPort());
        assertEquals(false, updated.enabled());
    }

    @Test
    void updateGb28181EntryNotFoundRejected() {
        Gb28181AccessConfigDao dao = mock(Gb28181AccessConfigDao.class);
        UUID id = UUID.randomUUID();
        when(dao.selectById(id)).thenReturn(null);

        assertThrows(IllegalArgumentException.class,
                () -> newService(mock(Ga1400AccessConfigDao.class), dao).updateGb28181Entry(id, validGb28181Entry()));
        verify(dao, never()).updateById(any(Gb28181AccessConfigEntity.class));
    }

    @Test
    void updateGb28181EntryRejectsInvalidRequest() {
        Gb28181AccessConfigDao dao = mock(Gb28181AccessConfigDao.class);
        Gb28181EntryRequest request = new Gb28181EntryRequest(true, "34020000002000000001", "3402000000",
                "192.168.1.10", "70000", "pw", "5061", "30000", "30100");

        assertThrows(IllegalArgumentException.class,
                () -> newService(mock(Ga1400AccessConfigDao.class), dao).updateGb28181Entry(UUID.randomUUID(), request));
        verify(dao, never()).updateById(any(Gb28181AccessConfigEntity.class));
    }

    @Test
    void deleteGb28181EntryDelegatesToDao() {
        Gb28181AccessConfigDao dao = mock(Gb28181AccessConfigDao.class);
        UUID id = UUID.randomUUID();

        newService(mock(Ga1400AccessConfigDao.class), dao).deleteGb28181Entry(id);

        verify(dao).deleteById(id);
    }
}
