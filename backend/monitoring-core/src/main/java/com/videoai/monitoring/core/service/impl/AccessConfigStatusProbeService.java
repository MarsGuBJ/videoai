package com.videoai.monitoring.core.service.impl;

import com.videoai.monitoring.core.dao.Ga1400AccessConfigDao;
import com.videoai.monitoring.core.dao.Gb28181AccessConfigDao;
import com.videoai.monitoring.core.entity.Ga1400AccessConfigEntity;
import com.videoai.monitoring.core.entity.Gb28181AccessConfigEntity;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/**
 * 接入配置在线状态探测（模块12 缺陷修复）：每 60s 对启用中的 GB28181/GA1400 条目做
 * TCP connect 探测，结果落库 online_status / last_check_at，并在 list 响应透出。
 * 探测在线程池中并行执行、单次连接 2.5s 超时，不阻塞调度线程。
 * 已知限制：GB28181 SIP 信令通常走 UDP 5060，TCP 探测对纯 UDP 端点会显示 OFFLINE。
 */
@Service
public class AccessConfigStatusProbeService {
    private static final Logger log = LoggerFactory.getLogger(AccessConfigStatusProbeService.class);
    private static final int CONNECT_TIMEOUT_MS = 2500;
    private static final long FUTURE_TIMEOUT_MS = 10000;
    private static final String ONLINE = "ONLINE";
    private static final String OFFLINE = "OFFLINE";
    private static final String UNKNOWN = "UNKNOWN";

    private final Gb28181AccessConfigDao gb28181AccessConfigDao;
    private final Ga1400AccessConfigDao ga1400AccessConfigDao;
    private final ExecutorService probeExecutor = Executors.newFixedThreadPool(4, runnable -> {
        Thread thread = new Thread(runnable, "access-config-probe");
        thread.setDaemon(true);
        return thread;
    });

    public AccessConfigStatusProbeService(Gb28181AccessConfigDao gb28181AccessConfigDao,
                                          Ga1400AccessConfigDao ga1400AccessConfigDao) {
        this.gb28181AccessConfigDao = gb28181AccessConfigDao;
        this.ga1400AccessConfigDao = ga1400AccessConfigDao;
    }

    @PreDestroy
    void shutdown() {
        probeExecutor.shutdownNow();
    }

    @Scheduled(fixedDelay = 60000, initialDelay = 60000)
    public void probeAll() {
        try {
            probeGb28181Entries();
            probeGa1400Entries();
        } catch (Exception exception) {
            log.warn("access_config_status_probe failed: {}", exception.getMessage());
        }
    }

    private void probeGb28181Entries() {
        List<Gb28181AccessConfigEntity> entries = gb28181AccessConfigDao.selectAllOrdered();
        OffsetDateTime now = OffsetDateTime.now();
        List<Gb28181AccessConfigEntity> probed = new ArrayList<>();
        List<CompletableFuture<String>> futures = new ArrayList<>();
        for (Gb28181AccessConfigEntity entry : entries) {
            if (!Boolean.TRUE.equals(entry.getEnabled())) {
                markGb28181UnknownIfChanged(entry);
                continue;
            }
            String host = clean(entry.getSipIp());
            Integer port = parsePort(entry.getSipPort());
            if (host == null || port == null) {
                gb28181AccessConfigDao.updateOnlineStatus(entry.getId(), UNKNOWN, now);
                continue;
            }
            probed.add(entry);
            futures.add(CompletableFuture.supplyAsync(() -> tcpProbe(host, port), probeExecutor));
        }
        for (int i = 0; i < probed.size(); i++) {
            gb28181AccessConfigDao.updateOnlineStatus(probed.get(i).getId(), await(futures.get(i)), now);
        }
    }

    private void probeGa1400Entries() {
        List<Ga1400AccessConfigEntity> entries = ga1400AccessConfigDao.selectAllOrdered();
        OffsetDateTime now = OffsetDateTime.now();
        List<Ga1400AccessConfigEntity> probed = new ArrayList<>();
        List<CompletableFuture<String>> futures = new ArrayList<>();
        for (Ga1400AccessConfigEntity entry : entries) {
            if (!Boolean.TRUE.equals(entry.getEnabled())) {
                markGa1400UnknownIfChanged(entry);
                continue;
            }
            String host = clean(entry.getPlatformIp());
            Integer port = parsePort(entry.getPort());
            if (host == null || port == null) {
                ga1400AccessConfigDao.updateOnlineStatus(entry.getId(), UNKNOWN, now);
                continue;
            }
            probed.add(entry);
            futures.add(CompletableFuture.supplyAsync(() -> tcpProbe(host, port), probeExecutor));
        }
        for (int i = 0; i < probed.size(); i++) {
            ga1400AccessConfigDao.updateOnlineStatus(probed.get(i).getId(), await(futures.get(i)), now);
        }
    }

    /** 停用条目不探测：仅在状态变化时落库 UNKNOWN，避免每轮空写。 */
    private void markGb28181UnknownIfChanged(Gb28181AccessConfigEntity entry) {
        if (!UNKNOWN.equals(entry.getOnlineStatus())) {
            gb28181AccessConfigDao.updateOnlineStatus(entry.getId(), UNKNOWN, entry.getLastCheckAt());
        }
    }

    private void markGa1400UnknownIfChanged(Ga1400AccessConfigEntity entry) {
        if (!UNKNOWN.equals(entry.getOnlineStatus())) {
            ga1400AccessConfigDao.updateOnlineStatus(entry.getId(), UNKNOWN, entry.getLastCheckAt());
        }
    }

    private static String await(CompletableFuture<String> future) {
        try {
            return future.get(FUTURE_TIMEOUT_MS, TimeUnit.MILLISECONDS);
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            return UNKNOWN;
        } catch (ExecutionException | TimeoutException exception) {
            return UNKNOWN;
        }
    }

    /** TCP connect 探测：可达 ONLINE，拒绝/超时/地址非法 OFFLINE。 */
    private static String tcpProbe(String host, int port) {
        try (Socket socket = new Socket()) {
            socket.connect(new InetSocketAddress(host, port), CONNECT_TIMEOUT_MS);
            return ONLINE;
        } catch (IOException | IllegalArgumentException | SecurityException exception) {
            return OFFLINE;
        }
    }

    private static Integer parsePort(String port) {
        String cleaned = clean(port);
        if (cleaned == null) {
            return null;
        }
        try {
            int value = Integer.parseInt(cleaned);
            return value >= 1 && value <= 65535 ? value : null;
        } catch (NumberFormatException exception) {
            return null;
        }
    }

    private static String clean(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }
}
