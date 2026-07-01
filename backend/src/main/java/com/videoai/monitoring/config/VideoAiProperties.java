package com.videoai.monitoring.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "videoai")
public record VideoAiProperties(
        Zlm zlm,
        Worker worker,
        Triton triton,
        Storage storage,
        Matching matching
) {
    public record Zlm(String httpUrl, String publicHttpUrl, String secret, String rtmpPushBase) {
    }

    public record Worker(String url) {
    }

    public record Triton(String httpUrl) {
    }

    public record Storage(String faceDir, String snapshotDir) {
    }

    public record Matching(double threshold, long cooldownSeconds) {
    }
}

