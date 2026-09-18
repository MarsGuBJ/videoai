package com.videoai.monitoring.core.service.impl;

import com.videoai.monitoring.core.client.ZlmClient;
import com.videoai.monitoring.core.config.VideoAiProperties;
import com.videoai.monitoring.core.service.LiveRelayService;
import com.videoai.monitoring.core.support.StreamUrls;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
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
    public boolean addZlmediakitProxy(String sourceUrl, String streamName) {
        return addZlmediakitProxy(sourceUrl, streamName, false);
    }

    @Override
    public boolean addZlmediakitProxy(String sourceUrl, String streamName, boolean forceRestart) {
        return addZlmediakitProxy(sourceUrl, streamName, forceRestart, false);
    }

    @Override
    public boolean addZlmediakitProxy(String sourceUrl, String streamName, boolean forceRestart, boolean audioTranscode) {
        if (sourceUrl == null || !sourceUrl.startsWith("rtsp://")) {
            // 非 RTSP 源（如内部推流）无需挂代理，不算失败
            return true;
        }
        if (audioTranscode || useFfmpegLiveRelay(streamName)) {
            return startFfmpegLiveRelay(sourceUrl, streamName, forceRestart, audioTranscode);
        }
        return zlmClient.addStreamProxy("live", streamName, sourceUrl);
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
    public boolean startFfmpegLiveRelay(String sourceUrl, String streamName, boolean forceRestart) {
        return startFfmpegLiveRelay(sourceUrl, streamName, forceRestart, false);
    }

    @Override
    public boolean startFfmpegLiveRelay(String sourceUrl, String streamName, boolean forceRestart, boolean withAudio) {
        Process existing = liveRelayProcesses.get(streamName);
        if (existing != null && existing.isAlive()) {
            if (!forceRestart) {
                return true;
            }
            terminateProcess(existing);
        }
        liveRelayProcesses.remove(streamName);

        zlmClient.closeStreams("live", streamName);
        String publishUrl = properties.zlm().rtmpPushBase() + "/" + StreamUrls.quote(streamName);
        List<String> command = new ArrayList<>(Arrays.asList(
                properties.ffmpegBin(),
                "-hide_banner",
                "-loglevel", "warning",
                "-rtsp_transport", "tcp",
                "-i", sourceUrl));
        if (withAudio) {
            // 视频透传；音频转 AAC（摄像头多为 G.711，浏览器 MSE 只支持 AAC/MP3）
            command.addAll(Arrays.asList("-c:v", "copy", "-c:a", "aac", "-b:a", "32k"));
        } else {
            command.addAll(Arrays.asList("-an", "-c:v", "copy"));
        }
        command.addAll(Arrays.asList("-f", "flv", publishUrl));
        Process process;
        try {
            // 注意：Redirect.DISCARD 不能用于 stdin（仅输出方向合法），ffmpeg 无输入命令源即可
            process = new ProcessBuilder(command)
                    .redirectOutput(ProcessBuilder.Redirect.DISCARD)
                    .redirectError(ProcessBuilder.Redirect.DISCARD)
                    .start();
        } catch (IOException exception) {
            log.warn("ffmpeg relay failed for {}: {}", streamName, exception.getMessage());
            return zlmClient.addStreamProxy("live", streamName, sourceUrl);
        }
        liveRelayProcesses.put(streamName, process);
        log.info("ffmpeg relay started for {} (audio={})", streamName, withAudio);
        return true;
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
