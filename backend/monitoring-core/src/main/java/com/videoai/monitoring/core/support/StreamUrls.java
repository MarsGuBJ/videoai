package com.videoai.monitoring.core.support;

import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Set;

/**
 * Playback/stream-name URL semantics ported from backend-lite/main.py
 * (stream_name_from_source, playback_url, is_internal_stream_url).
 */
public final class StreamUrls {
    private static final String LIVE_MARKER = "/live/";
    private static final Set<String> INTERNAL_STREAM_HOSTS =
            Set.of("zlm", "host.docker.internal", "172.21.0.1", "localhost", "127.0.0.1");

    private StreamUrls() {
    }

    public static String streamNameFromSource(String sourceUrl) {
        if (sourceUrl == null) {
            return null;
        }
        int marker = sourceUrl.indexOf(LIVE_MARKER);
        if (marker < 0) {
            return null;
        }
        String name = sourceUrl.substring(marker + LIVE_MARKER.length());
        while (name.endsWith("/")) {
            name = name.substring(0, name.length() - 1);
        }
        return name;
    }

    public static String playbackUrl(String publicHttpUrl, String sourceUrl, String fallbackStream) {
        String streamName = streamNameFromSource(sourceUrl);
        if (streamName == null || streamName.isEmpty()) {
            streamName = fallbackStream;
        }
        if (sourceUrl.startsWith("rtsp://")) {
            return liveFlvUrl(publicHttpUrl, streamName);
        }
        if (!streamName.isEmpty() && isInternalStreamUrl(sourceUrl)) {
            return liveFlvUrl(publicHttpUrl, streamName);
        }
        if (sourceUrl.startsWith("http://") || sourceUrl.startsWith("https://")) {
            return sourceUrl;
        }
        return "/api/streams/live/" + quote(streamName) + ".mjpeg";
    }

    public static String liveFlvUrl(String publicHttpUrl, String streamName) {
        return publicHttpUrl + "/live/" + quote(streamName) + ".live.flv";
    }

    public static boolean isInternalStreamUrl(String sourceUrl) {
        try {
            String host = URI.create(sourceUrl).getHost();
            return host != null && INTERNAL_STREAM_HOSTS.contains(host);
        } catch (IllegalArgumentException exception) {
            return false;
        }
    }

    /** Equivalent of Python's urllib.parse.quote(value, safe="") for typical segment names. */
    public static String quote(String value) {
        return URLEncoder.encode(value, StandardCharsets.UTF_8).replace("+", "%20");
    }

    public static String hostOf(String url) {
        try {
            return URI.create(url).getHost();
        } catch (IllegalArgumentException exception) {
            return null;
        }
    }
}
