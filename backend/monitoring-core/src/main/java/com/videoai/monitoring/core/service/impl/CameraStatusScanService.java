package com.videoai.monitoring.core.service.impl;

import com.videoai.monitoring.core.dao.CameraDao;
import com.videoai.monitoring.core.entity.CameraEntity;
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
 * 设备在线状态定时扫描：每 10 分钟对**全部设备**（RUNNING / STOPPED / DISABLED，含从未启动过的设备）
 * 的 sourceUrl 做 TCP connect 探测（线程池并行、单次 2 秒超时），结果写入 cameras.online_status：
 * 可达 ONLINE、不可达 OFFLINE、地址不可解析或内部推流地址 UNKNOWN（保持原值，等待人工确认）。
 *
 * <p>职责边界：本扫描只维护"设备是否可达"，不再改写 cameras.status（拉流状态由
 * {@link com.videoai.monitoring.core.service.CameraService} 的 start/stop 与
 * {@link StreamGuardServiceImpl} 的挂流结果维护）。历史上 status=OFFLINE 混用了两种语义，
 * V16 迁移已把历史 OFFLINE 拆成 status=RUNNING + online_status=OFFLINE。
 */
@Service
public class CameraStatusScanService {
    private static final Logger log = LoggerFactory.getLogger(CameraStatusScanService.class);
    private static final int CONNECT_TIMEOUT_MS = 2000;
    private static final long FUTURE_TIMEOUT_MS = 8000;
    private static final int PROBE_THREADS = 12;

    public static final String ONLINE = "ONLINE";
    public static final String OFFLINE = "OFFLINE";
    public static final String UNKNOWN = "UNKNOWN";

    private final CameraDao cameraDao;
    private final ExecutorService probeExecutor = Executors.newFixedThreadPool(PROBE_THREADS, runnable -> {
        Thread thread = new Thread(runnable, "camera-status-probe");
        thread.setDaemon(true);
        return thread;
    });

    public CameraStatusScanService(CameraDao cameraDao) {
        this.cameraDao = cameraDao;
    }

    @PreDestroy
    void shutdown() {
        probeExecutor.shutdownNow();
    }

    /** 本次扫描结果：total 为设备总数，其余为扫描后的分类计数，changed 为写库条数。 */
    public record ScanResult(int total, int online, int offline, int unknown, int changed) {
    }

    @Scheduled(fixedDelay = 600000, initialDelay = 60000)
    public void scan() {
        try {
            ScanResult result = scanOnce();
            log.info("camera_status_scan: total={} online={} offline={} unknown={} changed={}",
                    result.total(), result.online(), result.offline(), result.unknown(), result.changed());
        } catch (Exception exception) {
            log.warn("camera_status_scan failed: {}", exception.getMessage());
        }
    }

    /** 扫描全部设备并回写 online_status（仅在与当前值不同时写库）。synchronized：定时扫描与手工触发串行。 */
    public synchronized ScanResult scanOnce() {
        List<CameraEntity> probed = new ArrayList<>();
        List<CompletableFuture<Boolean>> futures = new ArrayList<>();
        int total = 0;
        int unknown = 0;
        int changed = 0;

        for (CameraEntity camera : cameraDao.selectAllOrdered()) {
            total += 1;
            HostPort target = parseTarget(camera.getSourceUrl());
            if (target == null) {
                // 内部推流地址或无法解析的地址：无法探测，标记为未知
                if (applyStatus(camera, UNKNOWN)) {
                    changed += 1;
                }
                unknown += 1;
                continue;
            }
            probed.add(camera);
            futures.add(CompletableFuture.supplyAsync(
                    () -> isReachable(target.host(), target.port()), probeExecutor));
        }

        int online = 0;
        int offline = 0;
        for (int i = 0; i < probed.size(); i += 1) {
            CameraEntity camera = probed.get(i);
            Boolean reachable = await(futures.get(i));
            if (reachable == null) {
                // 探测未在超时内返回：保留原状态，只计入未知
                unknown += 1;
                continue;
            }
            String status = reachable ? ONLINE : OFFLINE;
            if (applyStatus(camera, status)) {
                changed += 1;
                log.info("camera {} ({}) online_status -> {}", camera.getName(), camera.getId(), status);
            }
            if (reachable) {
                online += 1;
            } else {
                offline += 1;
            }
        }
        return new ScanResult(total, online, offline, unknown, changed);
    }

    /** 仅在状态需要变化时落库，避免每轮空写。 */
    private boolean applyStatus(CameraEntity camera, String status) {
        if (status.equals(camera.getOnlineStatus())) {
            return false;
        }
        cameraDao.updateOnlineStatus(camera.getId(), status);
        return true;
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
