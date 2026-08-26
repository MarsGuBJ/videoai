package com.videoai.monitoring.core.service.preview;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.videoai.monitoring.core.config.VideoAiProperties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpTimeoutException;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Port of backend-lite/preview_relay.py ZlmPreviewClient: starts/stops ZLMediaKit
 * addFFmpegSource relays that re-publish a camera RTSP source as preview-{stream}.
 */
@Component
public class ZlmPreviewClient {
    private static final Logger log = LoggerFactory.getLogger(ZlmPreviewClient.class);

    private final String baseUrl;
    private final String secret;
    private final String previewRtmpBase;
    private final String commandKey;
    private final long timeoutMs;
    private final HttpClient httpClient;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public ZlmPreviewClient(VideoAiProperties properties) {
        this.baseUrl = stripTrailingSlash(properties.zlm().httpUrl());
        this.secret = properties.zlm().secret();
        this.previewRtmpBase = stripTrailingSlash(properties.zlm().previewRtmpBase());
        this.commandKey = properties.preview().ffmpegCmdKey();
        this.timeoutMs = properties.preview().startTimeoutMs();
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .build();
    }

    public String baseUrl() {
        return baseUrl;
    }

    public String start(String streamName, String sourceUrl) {
        String derivedStream = previewStreamName(streamName);
        String destinationUrl = previewRtmpBase + "/" + derivedStream;
        try {
            Map<String, String> params = new LinkedHashMap<>();
            params.put("secret", secret);
            params.put("src_url", sourceUrl);
            params.put("dst_url", destinationUrl);
            params.put("timeout_ms", String.valueOf(timeoutMs));
            params.put("enable_hls", "0");
            params.put("enable_mp4", "0");
            params.put("ffmpeg_cmd_key", commandKey);
            JsonNode payload = request("/index/api/addFFmpegSource", params);
            String key = payload.path("data").path("key").asText("").trim();
            if (key.isEmpty()) {
                throw new PreviewRelayException("ZLMediaKit did not return a preview relay key");
            }
            return key;
        } catch (PreviewRelayException exception) {
            cleanupDestination(destinationUrl);
            throw exception;
        }
    }

    public void stop(String key) {
        Map<String, String> params = new LinkedHashMap<>();
        params.put("secret", secret);
        params.put("key", key);
        request("/index/api/delFFmpegSource", params);
    }

    private void cleanupDestination(String destinationUrl) {
        JsonNode payload;
        try {
            payload = request("/index/api/listFFmpegSource", Map.of("secret", secret));
        } catch (PreviewRelayException exception) {
            log.warn("Failed to inspect uncertain ZLMediaKit preview relay startup");
            return;
        }
        JsonNode sources = payload.path("data");
        if (!sources.isArray()) {
            return;
        }
        for (JsonNode source : sources) {
            if (!destinationUrl.equals(source.path("dst_url").asText(null))) {
                continue;
            }
            String key = source.path("key").asText("").trim();
            if (key.isEmpty()) {
                continue;
            }
            try {
                stop(key);
            } catch (PreviewRelayException exception) {
                log.warn("Failed to remove uncertain ZLMediaKit preview relay startup");
            }
        }
    }

    private JsonNode request(String path, Map<String, String> params) {
        String query = params.entrySet().stream()
                .map(entry -> encode(entry.getKey()) + "=" + encode(entry.getValue()))
                .collect(Collectors.joining("&"));
        HttpRequest request = HttpRequest.newBuilder(URI.create(baseUrl + path + "?" + query))
                .timeout(Duration.ofMillis(Math.max(1, timeoutMs) + 2000))
                .header("User-Agent", "VideoAI-Lite/1.0")
                .GET()
                .build();
        String body;
        try {
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            body = response.body();
        } catch (HttpTimeoutException exception) {
            throw new PreviewRelayException.Timeout("ZLMediaKit preview relay request timed out", exception);
        } catch (IOException exception) {
            throw new PreviewRelayException("ZLMediaKit preview relay request failed", exception);
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            throw new PreviewRelayException("ZLMediaKit preview relay request interrupted", exception);
        }

        JsonNode payload;
        try {
            payload = objectMapper.readTree(body);
        } catch (Exception exception) {
            throw new PreviewRelayException("ZLMediaKit returned an invalid preview relay response", exception);
        }
        if (!payload.isObject() || payload.path("code").asInt(-1) != 0) {
            String message = payload.path("msg").asText("");
            if (message.toLowerCase().contains("timeout")) {
                throw new PreviewRelayException.Timeout("ZLMediaKit preview relay request timed out");
            }
            throw new PreviewRelayException("ZLMediaKit rejected the preview relay request");
        }
        return payload;
    }

    public static String previewStreamName(String streamName) {
        return "preview-" + streamName;
    }

    private static String encode(String value) {
        return URLEncoder.encode(value, StandardCharsets.UTF_8);
    }

    private static String stripTrailingSlash(String value) {
        String result = value;
        while (result.endsWith("/")) {
            result = result.substring(0, result.length() - 1);
        }
        return result;
    }
}
