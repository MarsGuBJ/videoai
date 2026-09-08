package com.videoai.monitoring.core.service.impl;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.videoai.monitoring.common.dto.CertificateCreateRequest;
import com.videoai.monitoring.common.dto.CheckPortRequest;
import com.videoai.monitoring.common.dto.Ga1400Config;
import com.videoai.monitoring.common.dto.Ga1400EntryRequest;
import com.videoai.monitoring.common.dto.Gb28181Config;
import com.videoai.monitoring.common.dto.Gb28181EntryRequest;
import com.videoai.monitoring.common.vo.AccessConfigResponse;
import com.videoai.monitoring.common.vo.CertificateResponse;
import com.videoai.monitoring.common.vo.CheckPortResponse;
import com.videoai.monitoring.common.vo.Ga1400EntryResponse;
import com.videoai.monitoring.common.vo.Gb28181EntryResponse;
import com.videoai.monitoring.common.vo.HostIpsResponse;
import com.videoai.monitoring.core.dao.AccessConfigDao;
import com.videoai.monitoring.core.dao.DeviceCertificateDao;
import com.videoai.monitoring.core.dao.Ga1400AccessConfigDao;
import com.videoai.monitoring.core.dao.Gb28181AccessConfigDao;
import com.videoai.monitoring.core.entity.DeviceCertificateEntity;
import com.videoai.monitoring.core.entity.Ga1400AccessConfigEntity;
import com.videoai.monitoring.core.entity.Gb28181AccessConfigEntity;
import com.videoai.monitoring.core.service.AccessConfigService;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.NetworkInterface;
import java.net.ServerSocket;
import java.net.SocketException;
import java.time.OffsetDateTime;
import java.util.Enumeration;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import java.util.UUID;

@Service
public class AccessConfigServiceImpl implements AccessConfigService {
    private final AccessConfigDao accessConfigDao;
    private final DeviceCertificateDao deviceCertificateDao;
    private final Ga1400AccessConfigDao ga1400AccessConfigDao;
    private final Gb28181AccessConfigDao gb28181AccessConfigDao;
    private final ObjectMapper objectMapper;

    public AccessConfigServiceImpl(AccessConfigDao accessConfigDao, DeviceCertificateDao deviceCertificateDao,
                                   Ga1400AccessConfigDao ga1400AccessConfigDao,
                                   Gb28181AccessConfigDao gb28181AccessConfigDao, ObjectMapper objectMapper) {
        this.accessConfigDao = accessConfigDao;
        this.deviceCertificateDao = deviceCertificateDao;
        this.ga1400AccessConfigDao = ga1400AccessConfigDao;
        this.gb28181AccessConfigDao = gb28181AccessConfigDao;
        this.objectMapper = objectMapper;
    }

    @Override
    public AccessConfigResponse get() {
        return new AccessConfigResponse(
                load("gb28181", Gb28181Config.class),
                load("ga1400", Ga1400Config.class)
        );
    }

    @Override
    public Gb28181Config saveGb28181(Gb28181Config config) {
        AccessConfigService.validateGb28181(config);
        upsert("gb28181", config);
        return config;
    }

    @Override
    public Ga1400Config saveGa1400(Ga1400Config config) {
        AccessConfigService.validateGa1400(config);
        upsert("ga1400", config);
        return config;
    }

    @Override
    public List<Ga1400EntryResponse> listGa1400Entries() {
        return ga1400AccessConfigDao.selectAllOrdered().stream().map(this::toGa1400EntryResponse).toList();
    }

    @Override
    public Ga1400EntryResponse createGa1400Entry(Ga1400EntryRequest request) {
        AccessConfigService.validateGa1400Entry(request);
        UUID id = UUID.randomUUID();
        Ga1400AccessConfigEntity entity = new Ga1400AccessConfigEntity();
        entity.setId(id);
        applyGa1400Entry(entity, request);
        ga1400AccessConfigDao.insert(entity);
        return toGa1400EntryResponse(ga1400AccessConfigDao.selectById(id));
    }

    @Override
    public Ga1400EntryResponse updateGa1400Entry(UUID id, Ga1400EntryRequest request) {
        AccessConfigService.validateGa1400Entry(request);
        Ga1400AccessConfigEntity entity = ga1400AccessConfigDao.selectById(id);
        if (entity == null) {
            throw new IllegalArgumentException("GA1400 配置条目不存在: " + id);
        }
        applyGa1400Entry(entity, request);
        entity.setUpdatedAt(OffsetDateTime.now());
        ga1400AccessConfigDao.updateById(entity);
        return toGa1400EntryResponse(ga1400AccessConfigDao.selectById(id));
    }

    @Override
    public void deleteGa1400Entry(UUID id) {
        ga1400AccessConfigDao.deleteById(id);
    }

    @Override
    public List<Gb28181EntryResponse> listGb28181Entries() {
        return gb28181AccessConfigDao.selectAllOrdered().stream().map(this::toGb28181EntryResponse).toList();
    }

    @Override
    public Gb28181EntryResponse createGb28181Entry(Gb28181EntryRequest request) {
        AccessConfigService.validateGb28181Entry(request);
        UUID id = UUID.randomUUID();
        Gb28181AccessConfigEntity entity = new Gb28181AccessConfigEntity();
        entity.setId(id);
        applyGb28181Entry(entity, request);
        gb28181AccessConfigDao.insert(entity);
        return toGb28181EntryResponse(gb28181AccessConfigDao.selectById(id));
    }

    @Override
    public Gb28181EntryResponse updateGb28181Entry(UUID id, Gb28181EntryRequest request) {
        AccessConfigService.validateGb28181Entry(request);
        Gb28181AccessConfigEntity entity = gb28181AccessConfigDao.selectById(id);
        if (entity == null) {
            throw new IllegalArgumentException("GB28181 配置条目不存在: " + id);
        }
        applyGb28181Entry(entity, request);
        entity.setUpdatedAt(OffsetDateTime.now());
        gb28181AccessConfigDao.updateById(entity);
        return toGb28181EntryResponse(gb28181AccessConfigDao.selectById(id));
    }

    @Override
    public void deleteGb28181Entry(UUID id) {
        gb28181AccessConfigDao.deleteById(id);
    }

    @Override
    public List<CertificateResponse> listCertificates() {
        return deviceCertificateDao.selectAllOrdered().stream().map(this::toResponse).toList();
    }

    @Override
    public CertificateResponse createCertificate(CertificateCreateRequest request) {
        AccessConfigService.validateCertificate(request);
        UUID id = UUID.randomUUID();
        DeviceCertificateEntity entity = new DeviceCertificateEntity();
        entity.setId(id);
        entity.setDeviceCode(request.deviceCode().trim());
        entity.setCertificate(request.certificate());
        entity.setAuthMode(request.authMode().trim());
        deviceCertificateDao.insert(entity);
        return toResponse(deviceCertificateDao.selectById(id));
    }

    @Override
    public void deleteCertificate(UUID id) {
        deviceCertificateDao.deleteById(id);
    }

    @Override
    public HostIpsResponse hostIps() {
        Set<String> ips = new TreeSet<>();
        try {
            Enumeration<NetworkInterface> interfaces = NetworkInterface.getNetworkInterfaces();
            while (interfaces != null && interfaces.hasMoreElements()) {
                NetworkInterface networkInterface = interfaces.nextElement();
                if (!networkInterface.isUp() || networkInterface.isLoopback() || networkInterface.isVirtual()) {
                    continue;
                }
                Enumeration<InetAddress> addresses = networkInterface.getInetAddresses();
                while (addresses.hasMoreElements()) {
                    InetAddress address = addresses.nextElement();
                    if (address instanceof Inet4Address && !address.isLoopbackAddress()) {
                        ips.add(address.getHostAddress());
                    }
                }
            }
        } catch (SocketException exception) {
            throw new IllegalStateException("无法枚举本机网卡", exception);
        }
        return new HostIpsResponse(List.copyOf(ips));
    }

    @Override
    public CheckPortResponse checkPort(CheckPortRequest request) {
        int port = request.port();
        if (port < 1 || port > 65535) {
            throw new IllegalArgumentException("port 必须是 1-65535 的整数");
        }
        boolean available;
        try (ServerSocket socket = new ServerSocket()) {
            socket.setReuseAddress(false);
            socket.bind(new InetSocketAddress(port));
            available = true;
        } catch (IOException exception) {
            available = false;
        }
        return new CheckPortResponse(port, available);
    }

    private <T> T load(String protocol, Class<T> type) {
        return java.util.Optional.ofNullable(accessConfigDao.selectConfig(protocol))
                .map(json -> read(json, type))
                .orElse(null);
    }

    private void upsert(String protocol, Object config) {
        final String json;
        try {
            json = objectMapper.writeValueAsString(config);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("接入配置序列化失败", exception);
        }
        accessConfigDao.upsertConfig(protocol, json);
    }

    private <T> T read(String json, Class<T> type) {
        try {
            return objectMapper.readValue(json, type);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("接入配置反序列化失败", exception);
        }
    }

    private CertificateResponse toResponse(DeviceCertificateEntity entity) {
        return new CertificateResponse(
                entity.getId(),
                entity.getDeviceCode(),
                entity.getCertificate(),
                entity.getAuthMode(),
                entity.getCreatedAt(),
                entity.getUpdatedAt()
        );
    }

    private void applyGa1400Entry(Ga1400AccessConfigEntity entity, Ga1400EntryRequest request) {
        entity.setEnabled(request.enabled());
        entity.setPlatformId(request.platformId().trim());
        entity.setPlatformIp(request.platformIp() == null ? null : request.platformIp().trim());
        entity.setPort(request.port().trim());
        entity.setPassword(request.password());
        entity.setResourcePath(request.resourcePath());
        entity.setAutoRegister(request.autoRegister());
    }

    private Ga1400EntryResponse toGa1400EntryResponse(Ga1400AccessConfigEntity entity) {
        return new Ga1400EntryResponse(
                entity.getId(),
                Boolean.TRUE.equals(entity.getEnabled()),
                entity.getPlatformId(),
                entity.getPlatformIp(),
                entity.getPort(),
                entity.getPassword(),
                entity.getResourcePath(),
                Boolean.TRUE.equals(entity.getAutoRegister()),
                entity.getCreatedAt(),
                entity.getUpdatedAt()
        );
    }

    private void applyGb28181Entry(Gb28181AccessConfigEntity entity, Gb28181EntryRequest request) {
        entity.setEnabled(request.enabled());
        entity.setSipId(request.sipId().trim());
        entity.setSipDomain(request.sipDomain().trim());
        entity.setSipIp(request.sipIp() == null ? null : request.sipIp().trim());
        entity.setSipPort(request.sipPort().trim());
        entity.setPassword(request.password());
        entity.setParentPort(request.parentPort());
        entity.setReceivePortStart(request.receivePortStart().trim());
        entity.setReceivePortEnd(request.receivePortEnd().trim());
    }

    private Gb28181EntryResponse toGb28181EntryResponse(Gb28181AccessConfigEntity entity) {
        return new Gb28181EntryResponse(
                entity.getId(),
                Boolean.TRUE.equals(entity.getEnabled()),
                entity.getSipId(),
                entity.getSipDomain(),
                entity.getSipIp(),
                entity.getSipPort(),
                entity.getPassword(),
                entity.getParentPort(),
                entity.getReceivePortStart(),
                entity.getReceivePortEnd(),
                entity.getCreatedAt(),
                entity.getUpdatedAt()
        );
    }
}
