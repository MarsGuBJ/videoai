package com.videoai.monitoring.api;

import com.videoai.monitoring.common.dto.OpenSubscriptionRequest;
import com.videoai.monitoring.common.vo.OpenSubscriptionResponse;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;

import java.util.List;
import java.util.UUID;

/**
 * 对外开放订阅接口：第三方注册回调地址后，设备基础信息变化与
 * 在线/离线状态变化时主动向回调地址 POST 推送。注册成功后立即推送全量快照。
 * Implemented by a controller in monitoring-core.
 */
@RequestMapping("/api/open/subscriptions")
public interface OpenSubscriptionApi {

    @PostMapping
    OpenSubscriptionResponse subscribe(@Valid @RequestBody OpenSubscriptionRequest request);

    @DeleteMapping("/{subscriptionId}")
    void unsubscribe(@PathVariable UUID subscriptionId);

    @GetMapping
    List<OpenSubscriptionResponse> list();
}
