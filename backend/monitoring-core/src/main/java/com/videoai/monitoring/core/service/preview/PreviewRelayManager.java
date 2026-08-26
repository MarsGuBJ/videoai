package com.videoai.monitoring.core.service.preview;

import com.videoai.monitoring.core.config.VideoAiProperties;
import com.videoai.monitoring.core.support.StreamUrls;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.TimeUnit;

/**
 * Port of backend-lite/preview_relay.py PreviewRelayManager: reference-counted
 * preview relays with idle expiry, concurrent acquire waiting and explicit stop.
 */
@Component
public class PreviewRelayManager {
    private static final Logger log = LoggerFactory.getLogger(PreviewRelayManager.class);

    private final ZlmPreviewClient client;
    private final long idleSeconds;
    private final ScheduledExecutorService scheduler;
    private final Object lock = new Object();
    private final Map<String, RelayState> states = new HashMap<>();

    @Autowired
    public PreviewRelayManager(ZlmPreviewClient client, VideoAiProperties properties) {
        this(client, properties.preview().idleSeconds(), Executors.newSingleThreadScheduledExecutor(new ThreadFactory() {
            @Override
            public Thread newThread(Runnable runnable) {
                Thread thread = new Thread(runnable, "preview-relay-idle");
                thread.setDaemon(true);
                return thread;
            }
        }));
    }

    PreviewRelayManager(ZlmPreviewClient client, long idleSeconds, ScheduledExecutorService scheduler) {
        this.client = client;
        this.idleSeconds = idleSeconds;
        this.scheduler = scheduler;
    }

    public String acquire(String streamName, String sourceUrl) {
        while (true) {
            boolean owner = false;
            Signal waitForStart = null;
            Signal waitForStop = null;
            RelayState state;
            synchronized (lock) {
                state = states.get(streamName);
                if (state == null) {
                    state = new RelayState(sourceUrl);
                    state.viewers = 1;
                    states.put(streamName, state);
                    owner = true;
                } else if (state.stopping) {
                    waitForStop = state.stopped;
                } else if (!state.ready.isSet()) {
                    state.viewers += 1;
                    waitForStart = state.ready;
                } else if (state.error != null) {
                    states.remove(streamName);
                    continue;
                } else {
                    if (!state.sourceUrl.equals(sourceUrl)) {
                        throw new PreviewRelayException("Preview relay source changed while active");
                    }
                    if (state.idleTimer != null) {
                        state.idleTimer.cancel(false);
                        state.idleTimer = null;
                    }
                    state.viewers += 1;
                    return relayUrl(streamName);
                }
            }

            if (waitForStop != null) {
                waitForStop.await();
                if (state.error != null) {
                    throw state.error;
                }
                continue;
            }
            if (waitForStart != null) {
                waitForStart.await();
                if (state.error != null) {
                    throw state.error;
                }
                if (state.stopping) {
                    state.stopped.await();
                    continue;
                }
                return relayUrl(streamName);
            }
            if (owner) {
                return startOwned(streamName, sourceUrl, state);
            }
        }
    }

    public void release(String streamName) {
        synchronized (lock) {
            RelayState state = states.get(streamName);
            if (state == null || state.stopping || !state.ready.isSet()) {
                return;
            }
            state.viewers = Math.max(0, state.viewers - 1);
            if (state.viewers != 0 || state.idleTimer != null) {
                return;
            }
            state.idleTimer = scheduler.schedule(() -> expire(streamName, state), idleSeconds, TimeUnit.SECONDS);
        }
    }

    public void stopStream(String streamName) {
        RelayState state;
        boolean waitForExistingStop;
        synchronized (lock) {
            state = states.get(streamName);
            if (state == null) {
                return;
            }
            state.error = new PreviewRelayException("Preview relay was explicitly stopped");
            if (state.stopping) {
                waitForExistingStop = true;
            } else {
                waitForExistingStop = false;
                state.stopping = true;
                if (state.idleTimer != null) {
                    state.idleTimer.cancel(false);
                    state.idleTimer = null;
                }
            }
        }
        if (waitForExistingStop) {
            state.stopped.await();
            return;
        }
        state.ready.await();
        finishStop(streamName, state);
    }

    public void shutdown() {
        List<String> streamNames;
        synchronized (lock) {
            streamNames = new ArrayList<>(states.keySet());
        }
        for (String streamName : streamNames) {
            stopStream(streamName);
        }
    }

    public int viewerCount(String streamName) {
        synchronized (lock) {
            RelayState state = states.get(streamName);
            return state != null && !state.stopping ? state.viewers : 0;
        }
    }

    @PreDestroy
    void destroy() {
        shutdown();
        scheduler.shutdownNow();
    }

    private String startOwned(String streamName, String sourceUrl, RelayState state) {
        String key;
        try {
            key = client.start(streamName, sourceUrl);
        } catch (PreviewRelayException exception) {
            failStart(streamName, state, exception);
            throw exception;
        } catch (Exception exception) {
            PreviewRelayException error = new PreviewRelayException("ZLMediaKit preview relay request failed", exception);
            failStart(streamName, state, error);
            throw error;
        }

        boolean stopping;
        synchronized (lock) {
            state.key = key;
            state.ready.set();
            stopping = state.stopping;
        }
        if (stopping) {
            state.stopped.await();
            throw state.error != null ? state.error : new PreviewRelayException("Preview relay stopped during startup");
        }
        return relayUrl(streamName);
    }

    private void failStart(String streamName, RelayState state, PreviewRelayException error) {
        synchronized (lock) {
            state.error = error;
            if (states.get(streamName) == state) {
                states.remove(streamName);
            }
            state.ready.set();
            state.stopped.set();
        }
    }

    private void expire(String streamName, RelayState state) {
        synchronized (lock) {
            if (states.get(streamName) != state || state.viewers != 0 || state.stopping) {
                return;
            }
            state.stopping = true;
            state.idleTimer = null;
        }
        finishStop(streamName, state);
    }

    private void finishStop(String streamName, RelayState state) {
        try {
            if (state.key != null && !state.key.isEmpty()) {
                client.stop(state.key);
            }
        } catch (PreviewRelayException exception) {
            log.warn("Failed to stop ZLMediaKit preview relay for {}: {}", streamName, exception.getMessage());
        } finally {
            synchronized (lock) {
                if (states.get(streamName) == state) {
                    states.remove(streamName);
                }
                state.stopped.set();
            }
        }
    }

    private String relayUrl(String streamName) {
        String derivedStream = StreamUrls.quote(ZlmPreviewClient.previewStreamName(streamName));
        return client.baseUrl() + "/live/" + derivedStream + ".live.flv";
    }
}
