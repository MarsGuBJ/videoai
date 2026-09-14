package com.videoai.monitoring.core.validation;

import com.videoai.monitoring.common.dto.CameraCreateRequest;
import com.videoai.monitoring.common.dto.CameraUpdateRequest;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 设备创建/更新请求的字段校验：ip 为合法 IPv4、port 为 1-65535 整数、nvrChannel 为 1-256 整数；
 * 三个字段均为选填（null 放行）。
 */
class CameraRequestValidationTest {

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

    private static CameraCreateRequest createRequest(String ip, String port, String nvrChannel) {
        return new CameraCreateRequest(
                "测试设备", "rtsp://127.0.0.1:554/", null, null, null, nvrChannel, null, null,
                "RTSP 拉流", null, ip, port, null, null, null, null,
                null, null, null, null, null, null);
    }

    private static CameraUpdateRequest updateRequest(String ip, String port, String nvrChannel) {
        return new CameraUpdateRequest(
                null, null, null, null, null, nvrChannel, null, null,
                null, null, ip, port, null, null, null, null,
                null, null, null, null, null, null);
    }

    @Test
    void validValuesPass() {
        assertTrue(validator.validate(createRequest("192.168.1.64", "554", "1")).isEmpty());
        assertTrue(validator.validate(createRequest("10.10.7.252", "65535", "256")).isEmpty());
        assertTrue(validator.validate(updateRequest("192.168.1.64", "554", "32")).isEmpty());
    }

    @Test
    void nullOptionalValuesPass() {
        assertTrue(validator.validate(createRequest(null, null, null)).isEmpty());
        assertTrue(validator.validate(updateRequest(null, null, null)).isEmpty());
    }

    @Test
    void invalidIpRejected() {
        assertFalse(validator.validate(createRequest("999.999.999.999", "554", "1")).isEmpty());
        assertFalse(validator.validate(createRequest("192.168.1", "554", "1")).isEmpty());
        assertFalse(validator.validate(createRequest("abc", "554", "1")).isEmpty());
        assertFalse(validator.validate(updateRequest("999.999.999.999", null, null)).isEmpty());
    }

    @Test
    void invalidPortRejected() {
        assertFalse(validator.validate(createRequest(null, "abc", null)).isEmpty());
        assertFalse(validator.validate(createRequest(null, "0", null)).isEmpty());
        assertFalse(validator.validate(createRequest(null, "70000", null)).isEmpty());
        assertFalse(validator.validate(updateRequest(null, "70000", null)).isEmpty());
    }

    @Test
    void invalidChannelRejected() {
        assertFalse(validator.validate(createRequest(null, null, "0")).isEmpty());
        assertFalse(validator.validate(createRequest(null, null, "99999")).isEmpty());
        assertFalse(validator.validate(createRequest(null, null, "abc")).isEmpty());
        assertFalse(validator.validate(updateRequest(null, null, "0")).isEmpty());
    }
}
