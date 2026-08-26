package com.videoai.monitoring.api;

import com.videoai.monitoring.common.dto.CertificateCreateRequest;
import com.videoai.monitoring.common.dto.CheckPortRequest;
import com.videoai.monitoring.common.dto.Ga1400Config;
import com.videoai.monitoring.common.dto.Gb28181Config;
import com.videoai.monitoring.common.vo.AccessConfigResponse;
import com.videoai.monitoring.common.vo.CertificateResponse;
import com.videoai.monitoring.common.vo.CheckPortResponse;
import com.videoai.monitoring.common.vo.HostIpsResponse;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Access configuration (GB/T 28181, GA/T 1400, certificates) API contract.
 * Implemented by a controller in monitoring-core and proxied via Feign in
 * monitoring-api-rpc.
 */
@RequestMapping("/api/access-config")
public interface AccessConfigApi {

    @GetMapping
    AccessConfigResponse get();

    @PutMapping("/gb28181")
    Gb28181Config saveGb28181(@RequestBody Gb28181Config config);

    @PutMapping("/ga1400")
    Ga1400Config saveGa1400(@RequestBody Ga1400Config config);

    @GetMapping("/certificates")
    List<CertificateResponse> listCertificates();

    @PostMapping("/certificates")
    CertificateResponse createCertificate(@RequestBody CertificateCreateRequest request);

    @DeleteMapping("/certificates/{id}")
    Map<String, Object> deleteCertificate(@PathVariable UUID id);

    @GetMapping("/host-ip")
    HostIpsResponse hostIps();

    @PostMapping("/check-port")
    CheckPortResponse checkPort(@RequestBody CheckPortRequest request);
}
