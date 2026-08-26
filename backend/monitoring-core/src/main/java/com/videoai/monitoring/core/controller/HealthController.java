package com.videoai.monitoring.core.controller;

import com.videoai.monitoring.api.HealthApi;
import com.videoai.monitoring.common.vo.HealthResponse;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController implements HealthApi {

    @Override
    public HealthResponse health() {
        return new HealthResponse("ok");
    }
}
