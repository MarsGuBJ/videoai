package com.videoai.monitoring.api;

import com.videoai.monitoring.common.vo.OpenDeviceResponse;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

import java.util.List;
import java.util.UUID;

/**
 * 对外开放接口：匿名返回全部设备（在线+离线）列表，并按设备提供固定
 * FLV 视频流链接。流链接在请求时才动态建立视频流（按需挂流）。
 * Implemented by a controller in monitoring-core.
 */
@RequestMapping("/api/open/devices")
public interface OpenDeviceApi {

    @GetMapping
    List<OpenDeviceResponse> list();

    @GetMapping("/{deviceId}/live.flv")
    ResponseEntity<StreamingResponseBody> liveFlv(@PathVariable UUID deviceId);
}
