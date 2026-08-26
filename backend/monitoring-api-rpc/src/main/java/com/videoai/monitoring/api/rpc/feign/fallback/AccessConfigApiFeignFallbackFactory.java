package com.videoai.monitoring.api.rpc.feign.fallback;

import com.videoai.monitoring.api.rpc.feign.AccessConfigApiFeign;
import com.videoai.monitoring.common.dto.CertificateCreateRequest;
import com.videoai.monitoring.common.dto.CheckPortRequest;
import com.videoai.monitoring.common.dto.Ga1400Config;
import com.videoai.monitoring.common.dto.Gb28181Config;
import com.videoai.monitoring.common.vo.AccessConfigResponse;
import com.videoai.monitoring.common.vo.CertificateResponse;
import com.videoai.monitoring.common.vo.CheckPortResponse;
import com.videoai.monitoring.common.vo.HostIpsResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.openfeign.FallbackFactory;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@Slf4j
@Component
public class AccessConfigApiFeignFallbackFactory implements FallbackFactory<AccessConfigApiFeign> {
    @Override
    public AccessConfigApiFeign create(Throwable cause) {
        log.error("AccessConfigApi feign call failed, fallback triggered", cause);
        return new AccessConfigApiFeign() {
            @Override
            public AccessConfigResponse get() {
                return null;
            }

            @Override
            public Gb28181Config saveGb28181(Gb28181Config config) {
                return null;
            }

            @Override
            public Ga1400Config saveGa1400(Ga1400Config config) {
                return null;
            }

            @Override
            public List<CertificateResponse> listCertificates() {
                return List.of();
            }

            @Override
            public CertificateResponse createCertificate(CertificateCreateRequest request) {
                return null;
            }

            @Override
            public Map<String, Object> deleteCertificate(UUID id) {
                return null;
            }

            @Override
            public HostIpsResponse hostIps() {
                return null;
            }

            @Override
            public CheckPortResponse checkPort(CheckPortRequest request) {
                return null;
            }
        };
    }
}
