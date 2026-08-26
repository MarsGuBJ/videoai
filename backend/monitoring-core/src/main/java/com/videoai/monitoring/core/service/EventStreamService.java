package com.videoai.monitoring.core.service;

import com.videoai.monitoring.common.vo.FaceEventResponse;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

public interface EventStreamService {

    SseEmitter subscribe();

    void publish(FaceEventResponse event);
}
