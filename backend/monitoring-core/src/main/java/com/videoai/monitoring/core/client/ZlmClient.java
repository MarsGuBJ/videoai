package com.videoai.monitoring.core.client;

import com.videoai.monitoring.core.config.VideoAiProperties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.util.UriComponentsBuilder;

import java.util.Map;

@Component
public class ZlmClient {
    private static final Logger log = LoggerFactory.getLogger(ZlmClient.class);

    private final RestClient restClient;
    private final VideoAiProperties properties;

    public ZlmClient(RestClient restClient, VideoAiProperties properties) {
        this.restClient = restClient;
        this.properties = properties;
    }

    public Map<String, Object> addFfmpegSource(String sourceUrl, String dstUrl, String ffmpegCommandKey) {
        UriComponentsBuilder builder = UriComponentsBuilder.fromUriString(properties.zlm().httpUrl())
                .path("/index/api/addFFmpegSource")
                .queryParam("secret", properties.zlm().secret())
                .queryParam("src_url", sourceUrl)
                .queryParam("dst_url", dstUrl)
                .queryParam("timeout_ms", 15000);
        if (ffmpegCommandKey != null && !ffmpegCommandKey.isBlank()) {
            builder.queryParam("ffmpeg_cmd_key", ffmpegCommandKey);
        }
        String uri = builder.encode().toUriString();
        return requestMap(uri, "Failed to add FFmpeg source");
    }

    public Map<String, Object> setServerConfig(String key, String value) {
        String uri = UriComponentsBuilder.fromUriString(properties.zlm().httpUrl())
                .path("/index/api/setServerConfig")
                .queryParam("secret", properties.zlm().secret())
                .queryParam(key, value)
                .encode()
                .toUriString();
        return requestMap(uri, "Failed to set ZLMediaKit config");
    }

    public Map<String, Object> deleteFfmpegSource(String key) {
        String uri = UriComponentsBuilder.fromUriString(properties.zlm().httpUrl())
                .path("/index/api/delFFmpegSource")
                .queryParam("secret", properties.zlm().secret())
                .queryParam("key", key)
                .encode()
                .toUriString();
        return requestMap(uri, "Failed to delete FFmpeg source");
    }

    public Map<String, Object> mediaList() {
        String uri = UriComponentsBuilder.fromUriString(properties.zlm().httpUrl())
                .path("/index/api/getMediaList")
                .queryParam("secret", properties.zlm().secret())
                .encode()
                .toUriString();
        return requestMap(uri, "Failed to read media list");
    }

    /**
     * Mirrors backend-lite/main.py add_zlmediakit_stream_proxy: never throws.
     * 返回 true 表示 ZLM 已接受该代理（含"流已存在"这种幂等成功）；false 表示拉流服务拒绝了该地址
     * （例如 OPTIONS 404/401、通道非法），调用方据此避免把设备标成"拉流中"。
     */
    public boolean addStreamProxy(String app, String stream, String url) {
        String uri = UriComponentsBuilder.fromUriString(properties.zlm().httpUrl())
                .path("/index/api/addStreamProxy")
                .queryParam("secret", properties.zlm().secret())
                .queryParam("vhost", "__defaultVhost__")
                .queryParam("app", app)
                .queryParam("stream", stream)
                .queryParam("url", url)
                .queryParam("rtp_type", 0)
                .queryParam("enable_rtsp", 1)
                .queryParam("enable_rtmp", 1)
                .queryParam("enable_hls", 1)
                .queryParam("enable_fmp4", 1)
                .queryParam("enable_audio", 1)
                .queryParam("modify_stamp", 2)
                .queryParam("auto_close", 0)
                .encode()
                .toUriString();
        try {
            Map<String, Object> response = requestMap(uri, "ZLMediaKit addStreamProxy failed");
            Object code = response.get("code");
            if (code == null || "0".equals(code.toString())) {
                return true;
            }
            String message = response.get("msg") == null ? "" : response.get("msg").toString();
            // 代理已存在等价于挂流成功（重复调用/守护线程重挂场景）
            if (message.toLowerCase().contains("already exists")) {
                return true;
            }
            log.warn("ZLM addStreamProxy rejected for {}: {}", stream, response);
            return false;
        } catch (Exception exception) {
            log.warn("ZLM addStreamProxy failed for {}: {}", stream, exception.getMessage());
            return false;
        }
    }

    /** Mirrors backend-lite/main.py close_zlmediakit_stream (best effort). */
    public void closeStreams(String app, String stream) {
        String uri = UriComponentsBuilder.fromUriString(properties.zlm().httpUrl())
                .path("/index/api/close_streams")
                .queryParam("secret", properties.zlm().secret())
                .queryParam("vhost", "__defaultVhost__")
                .queryParam("app", app)
                .queryParam("stream", stream)
                .queryParam("force", 1)
                .encode()
                .toUriString();
        try {
            requestMap(uri, "ZLMediaKit close_streams failed");
        } catch (Exception exception) {
            log.debug("ZLM close_streams failed for {}: {}", stream, exception.getMessage());
        }
    }

    public Map<String, Object> listFFmpegSource() {
        String uri = UriComponentsBuilder.fromUriString(properties.zlm().httpUrl())
                .path("/index/api/listFFmpegSource")
                .queryParam("secret", properties.zlm().secret())
                .encode()
                .toUriString();
        return requestMap(uri, "Failed to list FFmpeg sources");
    }

    private Map<String, Object> requestMap(String uri, String message) {
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> response = restClient.get()
                    .uri(uri)
                    .retrieve()
                    .body(Map.class);
            return response == null ? Map.of() : response;
        } catch (Exception exception) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, message + ": " + exception.getMessage(), exception);
        }
    }
}
