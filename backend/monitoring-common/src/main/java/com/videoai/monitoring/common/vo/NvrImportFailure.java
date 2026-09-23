package com.videoai.monitoring.common.vo;

/** 从 NVR/CVR 导入：单台设备读取失败原因（不含凭据）。 */
public record NvrImportFailure(String host, String reason) {
}
