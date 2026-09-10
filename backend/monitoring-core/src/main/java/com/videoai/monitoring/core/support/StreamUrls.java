package com.videoai.monitoring.core.support;

import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Playback/stream-name URL semantics ported from backend-lite/main.py
 * (stream_name_from_source, playback_url, is_internal_stream_url).
 */
public final class StreamUrls {
    private static final String LIVE_MARKER = "/live/";
    private static final String SUB_STREAM_SUFFIX = "-sub";
    // 海康 RTSP：/Streaming/Channels/{通道}01 为主码流，{通道}02 为子码流
    private static final Pattern HIK_MAIN_CHANNEL = Pattern.compile("(/Streaming/Channels/\\d*?)01(?!\\d)");
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

    /**
     * 按厂商约定从主码流地址推导子码流地址；无法推导时返回 null（视为该设备无子码流）。
     * 海康：/Streaming/Channels/101 → 102；大华：subtype=0 → subtype=1。
     */
    public static String deriveSubSourceUrl(String sourceUrl) {
        if (sourceUrl == null || !sourceUrl.startsWith("rtsp://")) {
            return null;
        }
        Matcher hik = HIK_MAIN_CHANNEL.matcher(sourceUrl);
        if (hik.find()) {
            return hik.replaceFirst(Matcher.quoteReplacement(hik.group(1) + "02"));
        }
        if (sourceUrl.contains("subtype=0")) {
            return sourceUrl.replace("subtype=0", "subtype=1");
        }
        return null;
    }

    /** 子码流代理注册到 ZLM 时使用的流名（与主码流一一对应）。 */
    public static String subStreamName(String streamName) {
        return streamName == null ? null : streamName + SUB_STREAM_SUFFIX;
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
