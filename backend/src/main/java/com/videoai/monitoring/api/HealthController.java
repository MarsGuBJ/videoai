package com.videoai.monitoring.api;

import com.videoai.monitoring.dto.HealthResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {
    @GetMapping("/api/health")
    HealthResponse health() {
        return new HealthResponse("ok");
    }
}

