package com.videoai.monitoring.core.service.impl;

import com.videoai.monitoring.common.vo.FaceEventResponse;
import com.videoai.monitoring.core.service.EventStreamService;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

@Service
public class EventStreamServiceImpl implements EventStreamService {
    private final List<SseEmitter> emitters = new CopyOnWriteArrayList<>();

    @Override
    public SseEmitter subscribe() {
        SseEmitter emitter = new SseEmitter(0L);
        emitters.add(emitter);
        emitter.onCompletion(() -> emitters.remove(emitter));
        emitter.onTimeout(() -> emitters.remove(emitter));
        emitter.onError(error -> emitters.remove(emitter));
        try {
            emitter.send(SseEmitter.event().name("ready").data("ok"));
        } catch (IOException ignored) {
            emitters.remove(emitter);
        }
        return emitter;
    }

    @Override
    public void publish(FaceEventResponse event) {
        for (SseEmitter emitter : emitters) {
            try {
                emitter.send(SseEmitter.event().name("face-event").data(event));
            } catch (IOException exception) {
                emitters.remove(emitter);
            }
        }
    }
}
