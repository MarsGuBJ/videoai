package com.videoai.monitoring.api;

import com.videoai.monitoring.common.dto.NvrImportPrecheckRequest;
import com.videoai.monitoring.common.dto.NvrImportSyncRequest;
import com.videoai.monitoring.common.vo.CloudSyncResultResponse;
import com.videoai.monitoring.common.vo.NvrImportPrecheckResponse;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;

/**
 * 从 NVR/CVR 导入设备 API contract。Implemented by a controller in monitoring-core。
 */
@RequestMapping("/api/nvr-import")
public interface NvrImportApi {

    @PostMapping("/precheck")
    NvrImportPrecheckResponse precheck(@Valid @RequestBody NvrImportPrecheckRequest request);

    @PostMapping("/sync")
    CloudSyncResultResponse sync(@RequestBody NvrImportSyncRequest request);
}
