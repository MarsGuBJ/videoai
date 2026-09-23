package com.videoai.monitoring.core.service;

import com.videoai.monitoring.common.dto.NvrImportPrecheckRequest;
import com.videoai.monitoring.common.dto.NvrImportSyncRequest;
import com.videoai.monitoring.common.vo.CloudSyncResultResponse;
import com.videoai.monitoring.common.vo.NvrImportPrecheckResponse;

/** 从 NVR/CVR 导入设备：预检查（拉通道清单 + 判重）与同步入库。 */
public interface NvrImportService {

    NvrImportPrecheckResponse precheck(NvrImportPrecheckRequest request);

    CloudSyncResultResponse sync(NvrImportSyncRequest request);
}
