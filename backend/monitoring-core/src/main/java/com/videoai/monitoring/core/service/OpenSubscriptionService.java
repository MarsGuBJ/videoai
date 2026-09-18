package com.videoai.monitoring.core.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.videoai.monitoring.common.dto.OpenSubscriptionRequest;
import com.videoai.monitoring.common.vo.CameraResponse;
import com.videoai.monitoring.common.vo.DeviceEventMessage;
import com.videoai.monitoring.common.vo.OpenDeviceResponse;
import com.videoai.monitoring.common.vo.OpenSubscriptionResponse;
import com.videoai.monitoring.core.dao.OpenSubscriptionDao;
import com.videoai.monitoring.core.entity.OpenSubscriptionEntity;
import com.videoai.monitoring.core.support.OpenDevicePayloads;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Lazy;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * 设备变更订阅推送：订阅持久化在 open_subscriptions 表；
 * 推送为异步线程池逐个 POST（5 秒超时，失败仅记日志不重试，
 * 订阅方可用 GET /api/open/devices 兜底对账）。
 */
@Service
public class OpenSubscriptionService {
    private static final Logger log = LoggerFactory.getLogger(OpenSubscriptionService.class);
    private static final Duration PUSH_TIMEOUT = Duration.ofSeconds(5);

    private final OpenSubscriptionDao subscriptionDao;
    private final CameraService cameraService;
    private final ObjectMapper objectMapper;
    private final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(PUSH_TIMEOUT)
            .build();
    private final ExecutorService pushExecutor = Executors.newFixedThreadPool(4, runnable -> {
        Thread thread = new Thread(runnable, "open-subscription-push");
        thread.setDaemon(true);
        return thread;
    });

    public OpenSubscriptionService(OpenSubscriptionDao subscriptionDao,
                                   @Lazy CameraService cameraService,
                                   ObjectMapper objectMapper) {
        this.subscriptionDao = subscriptionDao;
        this.cameraService = cameraService;
        this.objectMapper = objectMapper;
    }

    @PreDestroy
    void shutdown() {
        pushExecutor.shutdownNow();
    }

    /** 注册订阅并异步推送全量设备快照。 */
    public OpenSubscriptionResponse subscribe(OpenSubscriptionRequest request) {
        OpenSubscriptionEntity entity = new OpenSubscriptionEntity();
        entity.setId(UUID.randomUUID());
        entity.setName(request.name());
        entity.setCallbackUrl(request.callbackUrl().trim());
        entity.setCreatedAt(OffsetDateTime.now());
        subscriptionDao.insert(entity);
        OpenSubscriptionResponse response = toResponse(entity);
        publishSnapshotTo(response);
        return response;
    }

    public void unsubscribe(UUID subscriptionId) {
        if (subscriptionDao.deleteById(subscriptionId) == 0) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Subscription not found");
        }
    }

    public List<OpenSubscriptionResponse> list() {
        return subscriptionDao.selectList(null).stream().map(this::toResponse).toList();
    }

    /** 向全部订阅方广播一条设备事件（异步，不阻塞调用方事务）。 */
    public void publish(String eventType, OpenDeviceResponse device) {
        DeviceEventMessage message = new DeviceEventMessage(eventType, OffsetDateTime.now(), device);
        pushExecutor.submit(() -> deliverToAll(message));
    }

    /** 设备事件的便捷入口：publish(eventType, camera) 一步到位。 */
    public void publishCamera(String eventType, CameraResponse camera) {
        publish(eventType, OpenDevicePayloads.toOpenDevice(camera));
    }

    /** 注册成功后向新订阅方逐台推送全量快照。 */
    private void publishSnapshotTo(OpenSubscriptionResponse subscription) {
        pushExecutor.submit(() -> {
            for (CameraResponse camera : cameraService.list()) {
                DeviceEventMessage message = new DeviceEventMessage(
                        DeviceEventMessage.SNAPSHOT, OffsetDateTime.now(),
                        OpenDevicePayloads.toOpenDevice(camera));
                deliver(subscription, message);
            }
        });
    }

    private void deliverToAll(DeviceEventMessage message) {
        for (OpenSubscriptionEntity entity : subscriptionDao.selectList(null)) {
            deliver(toResponse(entity), message);
        }
    }

    private void deliver(OpenSubscriptionResponse subscription, DeviceEventMessage message) {
        try {
            String body = objectMapper.writeValueAsString(message);
            HttpRequest request = HttpRequest.newBuilder(URI.create(subscription.callbackUrl()))
                    .timeout(PUSH_TIMEOUT)
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(body))
                    .build();
            HttpResponse<Void> response = httpClient.send(request, HttpResponse.BodyHandlers.discarding());
            if (response.statusCode() >= 400) {
                log.warn("open subscription push rejected: {} -> {} ({})",
                        subscription.callbackUrl(), response.statusCode(), message.eventType());
            }
        } catch (Exception exception) {
            log.warn("open subscription push failed: {} ({}): {}",
                    subscription.callbackUrl(), message.eventType(), exception.getMessage());
        }
    }

    private OpenSubscriptionResponse toResponse(OpenSubscriptionEntity entity) {
        return new OpenSubscriptionResponse(
                entity.getId(), entity.getName(), entity.getCallbackUrl(), entity.getCreatedAt());
    }
}
