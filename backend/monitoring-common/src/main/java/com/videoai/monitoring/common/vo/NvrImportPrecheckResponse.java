package com.videoai.monitoring.common.vo;

import com.videoai.monitoring.common.dto.NvrImportItem;

import java.util.List;

/** 从 NVR/CVR 导入：预检查响应（通道清单 + 判重结果 + 不可达设备）。 */
public record NvrImportPrecheckResponse(
        List<NvrImportItem> items,
        int newCount,
        int updateCount,
        List<NvrImportFailure> failures
) {
}
