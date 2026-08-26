package com.videoai.monitoring.core.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "videoai")
public record VideoAiProperties(
        Zlm zlm,
        Worker worker,
        Triton triton,
        Storage storage,
        Matching matching,
        Preview preview,
        Hikvision hikvision,
        String liveRtspRelayMode,
        String liveFfmpegRelayStreams,
        String dinoCameraHosts,
        String ffmpegBin
) {
    public record Zlm(String httpUrl, String publicHttpUrl, String secret, String rtmpPushBase, String previewRtmpBase) {
    }

    public record Worker(String url) {
    }

    public record Triton(String httpUrl) {
    }

    public record Storage(String faceDir, String snapshotDir, String cameraDir) {
    }

    public record Matching(double threshold, long cooldownSeconds) {
    }

    public record Preview(long idleSeconds, long startTimeoutMs, String ffmpegCmdKey) {
    }

    public record Hikvision(String nvrBaseUrl, String nvrUsername, String nvrPassword) {
    }
}
