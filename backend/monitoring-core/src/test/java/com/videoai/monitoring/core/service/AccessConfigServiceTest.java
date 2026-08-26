package com.videoai.monitoring.core.service;

import com.videoai.monitoring.common.dto.CertificateCreateRequest;
import com.videoai.monitoring.common.dto.Ga1400Config;
import com.videoai.monitoring.common.dto.Gb28181Config;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertThrows;

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
}
