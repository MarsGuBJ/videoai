package com.videoai.monitoring.core.service.preview;

import java.util.concurrent.ScheduledFuture;

/** Port of backend-lite/preview_relay.py RelayState. */
final class RelayState {
    final String sourceUrl;
    final Signal ready = new Signal();
    final Signal stopped = new Signal();
    String key;
    PreviewRelayException error;
    int viewers;
    ScheduledFuture<?> idleTimer;
    boolean stopping;

    RelayState(String sourceUrl) {
        this.sourceUrl = sourceUrl;
    }
}

/** Minimal threading.Event equivalent (set/isSet/await). */
final class Signal {
    private boolean set;

    synchronized void set() {
        set = true;
        notifyAll();
    }

    synchronized boolean isSet() {
        return set;
    }

    void await() {
        synchronized (this) {
            while (!set) {
                try {
                    wait();
                } catch (InterruptedException exception) {
                    Thread.currentThread().interrupt();
                    throw new PreviewRelayException("Interrupted while waiting for preview relay", exception);
                }
            }
        }
    }
}
