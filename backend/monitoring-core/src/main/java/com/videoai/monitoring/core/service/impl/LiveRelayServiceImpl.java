package com.videoai.monitoring.core.service.impl;

import com.videoai.monitoring.core.client.ZlmClient;
import com.videoai.monitoring.core.config.VideoAiProperties;
import com.videoai.monitoring.core.service.LiveRelayService;
import com.videoai.monitoring.core.support.StreamUrls;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.Arrays;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Service
public class LiveRelayServiceImpl implements LiveRelayService {
    private static final Logger log = LoggerFactory.getLogger(LiveRelayServiceImpl.class);
    private static final Set<String> FFMPEG_MODES = Set.of("ffmpeg", "all", "1", "true", "yes");
    private static final Set<String> ZLM_MODES = Set.of("zlm", "direct", "0", "false", "no");

    private final ZlmClient zlmClient;
    private final VideoAiProperties properties;
    private final Map<String, Process> liveRelayProcesses = new ConcurrentHashMap<>();

    public LiveRelayServiceImpl(ZlmClient zlmClient, VideoAiProperties properties) {
        this.zlmClient = zlmClient;
        this.properties = properties;
    }

    @Override
    public void addZlmediakitProxy(String sourceUrl, String streamName) {
        addZlmediakitProxy(sourceUrl, streamName, false);
    }

    @Override
    public void addZlmediakitProxy(String sourceUrl, String streamName, boolean forceRestart) {
        if (sourceUrl == null || !sourceUrl.startsWith("rtsp://")) {
            return;
        }
        if (useFfmpegLiveRelay(streamName)) {
            startFfmpegLiveRelay(sourceUrl, streamName, forceRestart);
            return;
        }
        zlmClient.addStreamProxy("live", streamName, sourceUrl);
    }

    @Override
    public void removeZlmediakitProxy(String streamName) {
        stopFfmpegLiveRelay(streamName);
        zlmClient.closeStreams("live", streamName);
    }

    @Override
    public boolean useFfmpegLiveRelay(String streamName) {
        String mode = properties.liveRtspRelayMode() == null
                ? "auto"
                : properties.liveRtspRelayMode().trim().toLowerCase();
        if (FFMPEG_MODES.contains(mode)) {
            return true;
        }
        if (ZLM_MODES.contains(mode)) {
            return false;
        }
        return ffmpegRelayStreams().contains(streamName);
    }

    @Override
    public void startFfmpegLiveRelay(String sourceUrl, String streamName, boolean forceRestart) {
        Process existing = liveRelayProcesses.get(streamName);
        if (existing != null && existing.isAlive()) {
            if (!forceRestart) {
                return;
            }
            terminateProcess(existing);
        }
        liveRelayProcesses.remove(streamName);

        zlmClient.closeStreams("live", streamName);
        String publishUrl = properties.zlm().rtmpPushBase() + "/" + StreamUrls.quote(streamName);
        Process process;
        try {
            process = new ProcessBuilder(
                    properties.ffmpegBin(),
                    "-hide_banner",
                    "-loglevel", "warning",
                    "-rtsp_transport", "tcp",
                    "-i", sourceUrl,
                    "-an",
                    "-c:v", "copy",
                    "-f", "flv",
                    publishUrl)
                    .redirectInput(ProcessBuilder.Redirect.DISCARD)
                    .redirectOutput(ProcessBuilder.Redirect.DISCARD)
                    .redirectError(ProcessBuilder.Redirect.DISCARD)
                    .start();
        } catch (IOException exception) {
            log.warn("ffmpeg relay failed for {}: {}", streamName, exception.getMessage());
            zlmClient.addStreamProxy("live", streamName, sourceUrl);
            return;
        }
        liveRelayProcesses.put(streamName, process);
        log.info("ffmpeg relay started for {}", streamName);
    }

    @Override
    public void stopFfmpegLiveRelay(String streamName) {
        Process process = liveRelayProcesses.remove(streamName);
        if (process != null && process.isAlive()) {
            terminateProcess(process);
        }
    }

    @Override
    public void stopAll() {
        for (String streamName : liveRelayProcesses.keySet().toArray(new String[0])) {
            stopFfmpegLiveRelay(streamName);
        }
    }

    private Set<String> ffmpegRelayStreams() {
        String configured = properties.liveFfmpegRelayStreams();
        if (configured == null || configured.isBlank()) {
            return Set.of();
        }
        return Arrays.stream(configured.split(","))
                .map(String::trim)
                .filter(item -> !item.isEmpty())
                .collect(Collectors.toSet());
    }

    private void terminateProcess(Process process) {
        process.destroy();
        try {
            if (!process.waitFor(4, TimeUnit.SECONDS)) {
                process.destroyForcibly();
                process.waitFor(2, TimeUnit.SECONDS);
            }
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            process.destroyForcibly();
        }
    }
}
