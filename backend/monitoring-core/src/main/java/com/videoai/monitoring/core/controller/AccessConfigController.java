package com.videoai.monitoring.core.controller;

import com.videoai.monitoring.api.AccessConfigApi;
import com.videoai.monitoring.common.dto.CertificateCreateRequest;
import com.videoai.monitoring.common.dto.CheckPortRequest;
import com.videoai.monitoring.common.dto.Ga1400Config;
import com.videoai.monitoring.common.dto.Gb28181Config;
import com.videoai.monitoring.common.vo.AccessConfigResponse;
import com.videoai.monitoring.common.vo.CertificateResponse;
import com.videoai.monitoring.common.vo.CheckPortResponse;
import com.videoai.monitoring.common.vo.HostIpsResponse;
import com.videoai.monitoring.core.service.AccessConfigService;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
public class AccessConfigController implements AccessConfigApi {
    private final AccessConfigService accessConfigService;

    public AccessConfigController(AccessConfigService accessConfigService) {
        this.accessConfigService = accessConfigService;
    }

    @Override
    public AccessConfigResponse get() {
        return accessConfigService.get();
    }

    @Override
    public Gb28181Config saveGb28181(Gb28181Config config) {
        return accessConfigService.saveGb28181(config);
    }

    @Override
    public Ga1400Config saveGa1400(Ga1400Config config) {
        return accessConfigService.saveGa1400(config);
    }

    @Override
    public List<CertificateResponse> listCertificates() {
        return accessConfigService.listCertificates();
    }

    @Override
    public CertificateResponse createCertificate(CertificateCreateRequest request) {
        return accessConfigService.createCertificate(request);
    }

    @Override
    public Map<String, Object> deleteCertificate(UUID id) {
        accessConfigService.deleteCertificate(id);
        return Map.of();
    }

    @Override
    public HostIpsResponse hostIps() {
        return accessConfigService.hostIps();
    }

    @Override
    public CheckPortResponse checkPort(CheckPortRequest request) {
        return accessConfigService.checkPort(request);
    }
}
