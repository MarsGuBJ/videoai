package com.videoai.monitoring.common.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;

/** 从 NVR/CVR 导入：预检查请求。hosts 元素支持 "IP" 或 "IP:端口"（端口默认 80）。 */
public record NvrImportPrecheckRequest(
        @NotEmpty String[] hosts,
        @NotBlank String username,
        @NotBlank String password
) {
}
