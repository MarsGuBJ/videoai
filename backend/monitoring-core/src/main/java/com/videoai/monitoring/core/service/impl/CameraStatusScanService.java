package com.videoai.monitoring.core.service.impl;

import com.videoai.monitoring.core.dao.CameraDao;
import com.videoai.monitoring.core.entity.CameraEntity;
import com.videoai.monitoring.core.service.LiveRelayService;
import com.videoai.monitoring.core.support.StreamUrls;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.URI;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/**
 * 设备在线状态定时扫描：每 10 分钟对 RUNNING/OFFLINE 摄像头的 sourceUrl 做
 * TCP connect 探测（线程池并行、单次 2.5s 超时），结果回写 cameras.status：
 * 探测失败 RUNNING → OFFLINE；恢复可达 OFFLINE → RUNNING 并重新挂 ZLM 流代理。
 * STOPPED（用户手动停止）与推流/地址不可解析的设备不探测，保持原状态。
 */
@Service
public class CameraStatusScanService {
    private static final Logger log = LoggerFactory.getLogger(CameraStatusScanService.class);
    private static final int CONNECT_TIMEOUT_MS = 2500;
    private static final long FUTURE_TIMEOUT_MS = 10000;
    private static final String RUNNING = "RUNNING";
    private static final String OFFLINE = "OFFLINE";

    private final CameraDao cameraDao;
    private final LiveRelayService liveRelayService;
    private final ExecutorService probeExecutor = Executors.newFixedThreadPool(4, runnable -> {
        Thread thread = new Thread(runnable, "camera-status-probe");
        thread.setDaemon(true);
        return thread;
    });

    public CameraStatusScanService(CameraDao cameraDao, LiveRelayService liveRelayService) {
        this.cameraDao = cameraDao;
        this.liveRelayService = liveRelayService;
    }

    @PreDestroy
    void shutdown() {
        probeExecutor.shutdownNow();
    }

    @Scheduled(fixedDelay = 600000, initialDelay = 600000)
    public void scan() {
        try {
            scanOnce();
        } catch (Exception exception) {
            log.warn("camera_status_scan failed: {}", exception.getMessage());
        }
    }

    void scanOnce() {
        List<CameraEntity> probed = new ArrayList<>();
        List<CompletableFuture<Boolean>> futures = new ArrayList<>();
        for (CameraEntity camera : cameraDao.selectAllOrdered()) {
            if (!RUNNING.equals(camera.getStatus()) && !OFFLINE.equals(camera.getStatus())) {
                continue;
            }
            HostPort target = parseTarget(camera.getSourceUrl());
            if (target == null) {
                continue;
            }
            probed.add(camera);
            futures.add(CompletableFuture.supplyAsync(() -> isReachable(target.host(), target.port()), probeExecutor));
        }
        for (int i = 0; i < probed.size(); i++) {
            applyResult(probed.get(i), await(futures.get(i)));
        }
    }

    /** 仅在状态需要变化时落库，避免每轮空写；恢复在线时重新挂主/子码流代理。 */
    private void applyResult(CameraEntity camera, Boolean reachable) {
        if (reachable == null) {
            return;
        }
        if (!reachable && RUNNING.equals(camera.getStatus())) {
            cameraDao.updateStatus(camera.getId(), OFFLINE);
            log.info("camera {} ({}) unreachable, marked OFFLINE", camera.getName(), camera.getId());
        } else if (reachable && OFFLINE.equals(camera.getStatus())) {
            cameraDao.updateStatus(camera.getId(), RUNNING);
            liveRelayService.addZlmediakitProxy(camera.getSourceUrl(), camera.getStreamName());
            String subSourceUrl = StreamUrls.deriveSubSourceUrl(camera.getSourceUrl());
            if (subSourceUrl != null) {
                liveRelayService.addZlmediakitProxy(subSourceUrl, StreamUrls.subStreamName(camera.getStreamName()));
            }
            log.info("camera {} ({}) reachable again, marked RUNNING", camera.getName(), camera.getId());
        }
    }

    /** TCP connect 探测：可达 true，拒绝/超时/地址非法 false。protected 便于测试覆盖。 */
    protected boolean isReachable(String host, int port) {
        try (Socket socket = new Socket()) {
            socket.connect(new InetSocketAddress(host, port), CONNECT_TIMEOUT_MS);
            return true;
        } catch (IOException | IllegalArgumentException | SecurityException exception) {
            return false;
        }
    }

    private static Boolean await(CompletableFuture<Boolean> future) {
        try {
            return future.get(FUTURE_TIMEOUT_MS, TimeUnit.MILLISECONDS);
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            return null;
        } catch (ExecutionException | TimeoutException exception) {
            return null;
        }
    }

    /** 从 sourceUrl 解析探测目标；推流（内部流地址）或无 host/未知 scheme 返回 null（不探测）。 */
    private static HostPort parseTarget(String sourceUrl) {
        if (sourceUrl == null || sourceUrl.isBlank() || StreamUrls.isInternalStreamUrl(sourceUrl)) {
            return null;
        }
        final URI uri;
        try {
            uri = URI.create(sourceUrl);
        } catch (IllegalArgumentException exception) {
            return null;
        }
        String host = uri.getHost();
        if (host == null) {
            return null;
        }
        int port = uri.getPort();
        if (port < 0) {
            String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase();
            port = switch (scheme) {
                case "rtsp", "rtsps" -> 554;
                case "rtmp" -> 1935;
                case "http" -> 80;
                case "https" -> 443;
                default -> -1;
            };
        }
        if (port < 0) {
            return null;
        }
        return new HostPort(host, port);
    }

    private record HostPort(String host, int port) {
    }
}
