package com.videoai.monitoring.core.controller;

import com.videoai.monitoring.api.NvrImportApi;
import com.videoai.monitoring.common.dto.NvrImportPrecheckRequest;
import com.videoai.monitoring.common.dto.NvrImportSyncRequest;
import com.videoai.monitoring.common.vo.CloudSyncResultResponse;
import com.videoai.monitoring.common.vo.NvrImportPrecheckResponse;
import com.videoai.monitoring.core.service.NvrImportService;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class NvrImportController implements NvrImportApi {

    private final NvrImportService nvrImportService;

    public NvrImportController(NvrImportService nvrImportService) {
        this.nvrImportService = nvrImportService;
    }

    @Override
    public NvrImportPrecheckResponse precheck(NvrImportPrecheckRequest request) {
        return nvrImportService.precheck(request);
    }

    @Override
    public CloudSyncResultResponse sync(NvrImportSyncRequest request) {
        return nvrImportService.sync(request);
    }
}
