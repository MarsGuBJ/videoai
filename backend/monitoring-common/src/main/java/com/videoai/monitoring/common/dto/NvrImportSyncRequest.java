package com.videoai.monitoring.common.dto;

import jakarta.validation.constraints.NotBlank;

import java.util.List;

/**
 * 从 NVR/CVR 导入：同步请求。items 为预检查后用户勾选的条目；账号密码用于回填设备凭据字段。
 * 导入为纯新增语义：已存在的设备（同源 IP）一律跳过，不做更新。
 */
public record NvrImportSyncRequest(
        List<NvrImportItem> items,
        String targetArea,
        @NotBlank String username,
        @NotBlank String password
) {
}
