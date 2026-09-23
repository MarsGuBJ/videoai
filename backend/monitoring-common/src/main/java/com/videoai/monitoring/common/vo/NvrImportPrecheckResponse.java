package com.videoai.monitoring.common.vo;

import com.videoai.monitoring.common.dto.NvrImportItem;

import java.util.List;

/**
 * 从 NVR/CVR 导入：预检查响应（通道清单 + 判重结果 + 不可达设备）。
 * newCount 为可新增的通道数；existingCount 为已存在设备（同源 IP）的通道数，导入时一律跳过、不更新。
 */
public record NvrImportPrecheckResponse(
        List<NvrImportItem> items,
        int newCount,
        int existingCount,
        List<NvrImportFailure> failures
) {
}
