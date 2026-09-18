package com.videoai.monitoring.core.service;

/**
 * Port of backend-lite/main.py live-relay helpers: add_zlmediakit_proxy,
 * use_ffmpeg_live_relay, start/stop_ffmpeg_live_relay, remove_zlmediakit_proxy.
 */
public interface LiveRelayService {

    /**
     * add_zlmediakit_proxy: rtsp sources go through ffmpeg relay or ZLM addStreamProxy.
     * Never throws; returns false only when the relay actually rejected/failed the source
     * (used by start() to avoid marking a device RUNNING while no stream was attached).
     */
    boolean addZlmediakitProxy(String sourceUrl, String streamName);

    boolean addZlmediakitProxy(String sourceUrl, String streamName, boolean forceRestart);

    /**
     * audioTranscode=true（设备支持音频）时走 ffmpeg 中继：视频透传、音频统一转 AAC——
     * 现场摄像头多为 G.711，浏览器 MSE 不支持，必须转码才能出声。
     */
    boolean addZlmediakitProxy(String sourceUrl, String streamName, boolean forceRestart, boolean audioTranscode);

    /** remove_zlmediakit_proxy. */
    void removeZlmediakitProxy(String streamName);

    boolean useFfmpegLiveRelay(String streamName);

    /** 启动 ffmpeg 转推；返回 false 表示未能启动（已回退 ZLM 代理，回退结果同样体现在返回值）。 */
    boolean startFfmpegLiveRelay(String sourceUrl, String streamName, boolean forceRestart);

    boolean startFfmpegLiveRelay(String sourceUrl, String streamName, boolean forceRestart, boolean withAudio);

    void stopFfmpegLiveRelay(String streamName);

    void stopAll();
}
