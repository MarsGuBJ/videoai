package com.videoai.monitoring.core.service.preview;

public class PreviewRelayException extends RuntimeException {
    public PreviewRelayException(String message) {
        super(message);
    }

    public PreviewRelayException(String message, Throwable cause) {
        super(message, cause);
    }

    public static class Timeout extends PreviewRelayException {
        public Timeout(String message) {
            super(message);
        }

        public Timeout(String message, Throwable cause) {
            super(message, cause);
        }
    }
}
