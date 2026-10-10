package com.videoai.monitoring.core.client;

import com.videoai.monitoring.common.vo.CameraResponse;
import com.videoai.monitoring.core.config.VideoAiProperties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.net.http.HttpClient;
import java.time.Duration;
import java.util.Map;

/**
 * MCP 平台服务（videoai-mcp-server）客户端：RTSP 不可用海康设备的 SDK 实时拉流兜底。
 *
 * 部分海康设备（现场为 DS-2TD 系列热成像相机）RTSP 服务拒绝连接但 SDK 8000 端口可用，
 * 由 MCP 服务用 HCNetSDK 实时取流经 ffmpeg 转封装推 ZLM，播放地址（ZLM FLV）与常规
 * RTSP 拉流完全一致。start 需要等待 ZLM 起流，超时给到 45s（MCP 侧自身上限约 30s）。
 */
@Component
public class McpLivePullClient {
    private static final Logger log = LoggerFactory.getLogger(McpLivePullClient.class);
    private static final int SDK_PORT = 8000;

    private final RestClient restClient;
    private final VideoAiProperties properties;

    public McpLivePullClient(VideoAiProperties properties) {
        this.properties = properties;
        HttpClient httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .build();
        JdkClientHttpRequestFactory requestFactory = new JdkClientHttpRequestFactory(httpClient);
        requestFactory.setReadTimeout(Duration.ofSeconds(45));
        this.restClient = RestClient.builder().requestFactory(requestFactory).build();
    }

    /** 启动一路 SDK 实时拉流；成功推流到 ZLM 后返回 true。 */
    public boolean startPull(CameraResponse camera) {
        try {
            Map<String, Object> response = restClient.post()
                    .uri(properties.mcp().baseUrl() + "/live-pull/start")
                    .body(Map.of(
                            "streamName", camera.streamName(),
                            "sourceUrl", camera.sourceUrl(),
                            "sdkPort", SDK_PORT))
                    .retrieve()
                    .body(Map.class);
            boolean pushed = response != null && response.get("data") != null;
            log.info("mcp live-pull start for {}: {}", camera.streamName(), pushed);
            return pushed;
        } catch (Exception exception) {
            log.warn("mcp live-pull start failed for {}: {}", camera.streamName(), exception.getMessage());
            return false;
        }
    }

    /** 停止一路 SDK 实时拉流（尽力而为，失败不影响关流主流程）。 */
    public void stopPull(String streamName) {
        try {
            restClient.post()
                    .uri(properties.mcp().baseUrl() + "/live-pull/stop")
                    .body(Map.of("streamName", streamName))
                    .retrieve()
                    .toBodilessEntity();
        } catch (Exception exception) {
            log.debug("mcp live-pull stop failed for {}: {}", streamName, exception.getMessage());
        }
    }
}
