package com.videoai.monitoring.core.service;

import org.springframework.boot.ApplicationRunner;

/**
 * Port of backend-lite/main.py stream_proxy_guard_loop + restore_running_camera_streams:
 * reconciles ZLM active streams against RUNNING cameras every 30s and re-attaches missing ones.
 */
public interface StreamGuardService extends ApplicationRunner {

    void restoreRunningCameraStreams();

    void reconcileStreams();
}
