package com.videoai.monitoring.common.dto;

public record CertificateCreateRequest(
        String deviceCode,
        String certificate,
        String authMode
) {
}
