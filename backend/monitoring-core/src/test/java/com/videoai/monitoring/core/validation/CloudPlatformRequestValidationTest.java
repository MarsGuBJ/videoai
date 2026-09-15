package com.videoai.monitoring.core.validation;

import com.videoai.monitoring.common.dto.CloudPlatformCreateRequest;
import com.videoai.monitoring.common.dto.CloudPlatformUpdateRequest;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 云平台创建/更新请求的字段校验（TC-YPT-003）：ip 为合法 IPv4、port 为 1-65535 整数；
 * 正则与 message 与 CameraCreateRequest 保持一致。
 */
class CloudPlatformRequestValidationTest {

    private static ValidatorFactory factory;
    private static Validator validator;

    @BeforeAll
    static void setUp() {
        factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
    }

    @AfterAll
    static void tearDown() {
        factory.close();
    }

    private static CloudPlatformCreateRequest createRequest(String ip, String port) {
        return new CloudPlatformCreateRequest("平台A", "GA1400", "app-key", "app-secret", ip, port);
    }

    private static CloudPlatformUpdateRequest updateRequest(String ip, String port) {
        return new CloudPlatformUpdateRequest("平台A", "GA1400", "app-key", "app-secret", ip, port);
    }

    @Test
    void validValuesPass() {
        assertTrue(validator.validate(createRequest("192.168.1.64", "8080")).isEmpty());
        assertTrue(validator.validate(createRequest("10.10.7.252", "65535")).isEmpty());
        assertTrue(validator.validate(updateRequest("192.168.1.64", "1")).isEmpty());
    }

    @Test
    void invalidIpRejected() {
        assertFalse(validator.validate(createRequest("999.999.999.999", "8080")).isEmpty());
        assertFalse(validator.validate(createRequest("192.168.1", "8080")).isEmpty());
        assertFalse(validator.validate(createRequest("abc", "8080")).isEmpty());
        assertFalse(validator.validate(updateRequest("999.999.999.999", "8080")).isEmpty());
    }

    @Test
    void invalidPortRejected() {
        assertFalse(validator.validate(createRequest("192.168.1.64", "abc")).isEmpty());
        assertFalse(validator.validate(createRequest("192.168.1.64", "0")).isEmpty());
        assertFalse(validator.validate(createRequest("192.168.1.64", "70000")).isEmpty());
        assertFalse(validator.validate(updateRequest("192.168.1.64", "70000")).isEmpty());
    }
}
