package com.videoai.monitoring.common.dto;

import jakarta.validation.constraints.NotBlank;

import java.util.List;

/** 从 NVR/CVR 导入：同步请求。items 为预检查后用户勾选的条目；账号密码用于回填设备凭据字段。 */
public record NvrImportSyncRequest(
        List<NvrImportItem> items,
        String targetArea,
        boolean overwrite,
        @NotBlank String username,
        @NotBlank String password
) {
}
