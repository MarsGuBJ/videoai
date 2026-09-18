package com.videoai.monitoring.core.controller;

import com.videoai.monitoring.api.OpenSubscriptionApi;
import com.videoai.monitoring.common.dto.OpenSubscriptionRequest;
import com.videoai.monitoring.common.vo.OpenSubscriptionResponse;
import com.videoai.monitoring.core.service.OpenSubscriptionService;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

@RestController
public class OpenSubscriptionController implements OpenSubscriptionApi {

    private final OpenSubscriptionService subscriptionService;

    public OpenSubscriptionController(OpenSubscriptionService subscriptionService) {
        this.subscriptionService = subscriptionService;
    }

    @Override
    public OpenSubscriptionResponse subscribe(OpenSubscriptionRequest request) {
        return subscriptionService.subscribe(request);
    }

    @Override
    public void unsubscribe(UUID subscriptionId) {
        subscriptionService.unsubscribe(subscriptionId);
    }

    @Override
    public List<OpenSubscriptionResponse> list() {
        return subscriptionService.list();
    }
}
