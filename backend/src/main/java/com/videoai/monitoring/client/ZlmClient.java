package com.videoai.monitoring.client;

import com.videoai.monitoring.config.VideoAiProperties;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.util.UriComponentsBuilder;

import java.util.Map;

@Component
public class ZlmClient {
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
