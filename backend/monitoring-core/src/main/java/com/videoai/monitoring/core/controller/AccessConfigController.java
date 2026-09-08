package com.videoai.monitoring.core.controller;

import com.videoai.monitoring.api.AccessConfigApi;
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
    public List<Ga1400EntryResponse> listGa1400Entries() {
        return accessConfigService.listGa1400Entries();
    }

    @Override
    public Ga1400EntryResponse createGa1400Entry(Ga1400EntryRequest request) {
        return accessConfigService.createGa1400Entry(request);
    }

    @Override
    public Ga1400EntryResponse updateGa1400Entry(UUID id, Ga1400EntryRequest request) {
        return accessConfigService.updateGa1400Entry(id, request);
    }

    @Override
    public Map<String, Object> deleteGa1400Entry(UUID id) {
        accessConfigService.deleteGa1400Entry(id);
        return Map.of();
    }

    @Override
    public List<Gb28181EntryResponse> listGb28181Entries() {
        return accessConfigService.listGb28181Entries();
    }

    @Override
    public Gb28181EntryResponse createGb28181Entry(Gb28181EntryRequest request) {
        return accessConfigService.createGb28181Entry(request);
    }

    @Override
    public Gb28181EntryResponse updateGb28181Entry(UUID id, Gb28181EntryRequest request) {
        return accessConfigService.updateGb28181Entry(id, request);
    }

    @Override
    public Map<String, Object> deleteGb28181Entry(UUID id) {
        accessConfigService.deleteGb28181Entry(id);
        return Map.of();
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
