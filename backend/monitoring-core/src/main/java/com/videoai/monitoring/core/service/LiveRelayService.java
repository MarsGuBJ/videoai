package com.videoai.monitoring.core.service;

/**
 * Port of backend-lite/main.py live-relay helpers: add_zlmediakit_proxy,
 * use_ffmpeg_live_relay, start/stop_ffmpeg_live_relay, remove_zlmediakit_proxy.
 */
public interface LiveRelayService {

    /** add_zlmediakit_proxy: rtsp sources go through ffmpeg relay or ZLM addStreamProxy. Never throws. */
    void addZlmediakitProxy(String sourceUrl, String streamName);

    void addZlmediakitProxy(String sourceUrl, String streamName, boolean forceRestart);

    /** remove_zlmediakit_proxy. */
    void removeZlmediakitProxy(String streamName);

    boolean useFfmpegLiveRelay(String streamName);

    void startFfmpegLiveRelay(String sourceUrl, String streamName, boolean forceRestart);

    void stopFfmpegLiveRelay(String streamName);

    void stopAll();
}
