package com.videoai.monitoring.core.service.impl;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.videoai.monitoring.common.dto.CertificateCreateRequest;
import com.videoai.monitoring.common.dto.CheckPortRequest;
import com.videoai.monitoring.common.dto.Ga1400Config;
import com.videoai.monitoring.common.dto.Gb28181Config;
import com.videoai.monitoring.common.vo.AccessConfigResponse;
import com.videoai.monitoring.common.vo.CertificateResponse;
import com.videoai.monitoring.common.vo.CheckPortResponse;
import com.videoai.monitoring.common.vo.HostIpsResponse;
import com.videoai.monitoring.core.dao.AccessConfigDao;
import com.videoai.monitoring.core.dao.DeviceCertificateDao;
import com.videoai.monitoring.core.entity.DeviceCertificateEntity;
import com.videoai.monitoring.core.service.AccessConfigService;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.NetworkInterface;
import java.net.ServerSocket;
import java.net.SocketException;
import java.util.Enumeration;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import java.util.UUID;

@Service
public class AccessConfigServiceImpl implements AccessConfigService {
    private final AccessConfigDao accessConfigDao;
    private final DeviceCertificateDao deviceCertificateDao;
    private final ObjectMapper objectMapper;

    public AccessConfigServiceImpl(AccessConfigDao accessConfigDao, DeviceCertificateDao deviceCertificateDao,
                                   ObjectMapper objectMapper) {
        this.accessConfigDao = accessConfigDao;
        this.deviceCertificateDao = deviceCertificateDao;
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
}
