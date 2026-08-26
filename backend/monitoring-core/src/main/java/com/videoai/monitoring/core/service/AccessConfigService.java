package com.videoai.monitoring.core.service;

import com.videoai.monitoring.common.dto.CertificateCreateRequest;
import com.videoai.monitoring.common.dto.CheckPortRequest;
import com.videoai.monitoring.common.dto.Ga1400Config;
import com.videoai.monitoring.common.dto.Gb28181Config;
import com.videoai.monitoring.common.vo.AccessConfigResponse;
import com.videoai.monitoring.common.vo.CertificateResponse;
import com.videoai.monitoring.common.vo.CheckPortResponse;
import com.videoai.monitoring.common.vo.HostIpsResponse;

import java.util.List;
import java.util.Set;
import java.util.UUID;

public interface AccessConfigService {

    Set<String> AUTH_MODES = Set.of("单向", "双向");

    AccessConfigResponse get();

    Gb28181Config saveGb28181(Gb28181Config config);

    Ga1400Config saveGa1400(Ga1400Config config);

    List<CertificateResponse> listCertificates();

    CertificateResponse createCertificate(CertificateCreateRequest request);

    void deleteCertificate(UUID id);

    HostIpsResponse hostIps();

    CheckPortResponse checkPort(CheckPortRequest request);

    static void validateGb28181(Gb28181Config config) {
        if (config == null) {
            throw new IllegalArgumentException("配置不能为空");
        }
        requireDigits(config.sipId(), 20, "sipId");
        requireDigits(config.sipDomain(), 10, "sipDomain");
        parsePort(config.sipPort(), "sipPort");
        int start = parsePort(config.receivePortStart(), "receivePortStart");
        int end = parsePort(config.receivePortEnd(), "receivePortEnd");
        if (start > end) {
            throw new IllegalArgumentException("receivePortStart 不能大于 receivePortEnd");
        }
    }

    static void validateGa1400(Ga1400Config config) {
        if (config == null) {
            throw new IllegalArgumentException("配置不能为空");
        }
        requireDigits(config.platformId(), 20, "platformId");
        parsePort(config.port(), "port");
    }

    static void validateCertificate(CertificateCreateRequest request) {
        if (request == null) {
            throw new IllegalArgumentException("请求不能为空");
        }
        requireDigits(request.deviceCode(), 20, "deviceCode");
        if (request.certificate() == null || request.certificate().isBlank()) {
            throw new IllegalArgumentException("certificate 不能为空");
        }
        if (request.authMode() == null || !AUTH_MODES.contains(request.authMode().trim())) {
            throw new IllegalArgumentException("authMode 只支持 单向/双向");
        }
    }

    private static void requireDigits(String value, int length, String field) {
        if (value == null || !value.matches("\\d{" + length + "}")) {
            throw new IllegalArgumentException(field + " 必须是 " + length + " 位数字");
        }
    }

    private static int parsePort(String value, String field) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(field + " 不能为空");
        }
        final int port;
        try {
            port = Integer.parseInt(value.trim());
        } catch (NumberFormatException exception) {
            throw new IllegalArgumentException(field + " 必须是 1-65535 的整数");
        }
        if (port < 1 || port > 65535) {
            throw new IllegalArgumentException(field + " 必须是 1-65535 的整数");
        }
        return port;
    }
}
