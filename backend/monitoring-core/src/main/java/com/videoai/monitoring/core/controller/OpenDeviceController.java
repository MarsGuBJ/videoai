package com.videoai.monitoring.core.controller;

import com.videoai.monitoring.api.OpenDeviceApi;
import com.videoai.monitoring.common.vo.CameraResponse;
import com.videoai.monitoring.common.vo.OpenDeviceResponse;
import com.videoai.monitoring.core.config.VideoAiProperties;
import com.videoai.monitoring.core.service.CameraService;
import com.videoai.monitoring.core.support.OpenDevicePayloads;
import com.videoai.monitoring.core.support.StreamUrls;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

/**
 * 对外开放接口实现：设备列表 + 按需建流的固定 FLV 链接。
 * FLV 代理逻辑与 MediaStreamController.proxyFlvStream 一致（含 ZLM 启动
 * 窗口内的 404 重试），差别仅在于这里对非 RUNNING 设备先自动开播。
 */
@RestController
public class OpenDeviceController implements OpenDeviceApi {
    private static final Logger log = LoggerFactory.getLogger(OpenDeviceController.class);

    private final CameraService cameraService;
    private final VideoAiProperties properties;
    private final HttpClient httpClient;

    public OpenDeviceController(CameraService cameraService, VideoAiProperties properties) {
        this.cameraService = cameraService;
        this.properties = properties;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .build();
    }

    @Override
    public List<OpenDeviceResponse> list() {
        return cameraService.list().stream()
                .map(OpenDevicePayloads::toOpenDevice)
                .toList();
    }

    @Override
    public ResponseEntity<StreamingResponseBody> liveFlv(UUID deviceId) {
        CameraResponse camera = cameraService.get(deviceId);
        if (camera.sourceUrl() == null || camera.sourceUrl().isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "该设备未配置拉流地址，无法提供视频流");
        }
        // 请求时动态建立视频流：未开播的设备先挂流（含可推导的子码流）
        if (!"RUNNING".equals(camera.status())) {
            log.info("open api auto-starting camera {} ({})", camera.name(), deviceId);
            camera = cameraService.start(deviceId);
        }
        String remoteUrl = properties.zlm().httpUrl()
                + "/live/" + StreamUrls.quote(camera.streamName()) + ".live.flv";

        HttpResponse<InputStream> response;
        try {
            response = openLiveRemote(remoteUrl);
        } catch (Exception exception) {
            if (exception instanceof ResponseStatusException statusException) {
                throw statusException;
            }
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Live stream unavailable", exception);
        }

        StreamingResponseBody body = outputStream -> {
            try (InputStream input = response.body()) {
                input.transferTo(outputStream);
            }
        };
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_TYPE, "video/x-flv")
                .body(body);
    }

    /** 直播流刚启动时 ZLM 可能尚未就绪：在启动超时窗口内对 404 重试。 */
    private HttpResponse<InputStream> openLiveRemote(String remoteUrl) {
        long timeoutMs = Math.max(1, properties.preview().startTimeoutMs());
        long deadline = System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(timeoutMs);
        while (true) {
            try {
                return openRemote(remoteUrl, Duration.ofSeconds(8));
            } catch (ResponseStatusException exception) {
                if (exception.getStatusCode().value() != 404 || System.nanoTime() >= deadline) {
                    throw exception;
                }
                try {
                    Thread.sleep(250);
                } catch (InterruptedException interrupted) {
                    Thread.currentThread().interrupt();
                    throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Live stream unavailable", interrupted);
                }
            }
        }
    }

    /** HTTP errors keep their status code, connection failures map to 502. */
    private HttpResponse<InputStream> openRemote(String url, Duration timeout) {
        HttpRequest request = HttpRequest.newBuilder(URI.create(url))
                .timeout(timeout)
                .header("User-Agent", "VideoAI-Lite/1.0")
                .GET()
                .build();
        HttpResponse<InputStream> response;
        try {
            response = httpClient.send(request, HttpResponse.BodyHandlers.ofInputStream());
        } catch (IOException exception) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY,
                    "SRS stream unavailable: " + exception.getMessage(), exception);
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "SRS stream unavailable", exception);
        }
        if (response.statusCode() >= 400) {
            int status = response.statusCode();
            try {
                response.body().close();
            } catch (IOException ignored) {
                // best effort
            }
            throw new ResponseStatusException(HttpStatus.valueOf(status), "SRS stream request failed");
        }
        return response;
    }
}
