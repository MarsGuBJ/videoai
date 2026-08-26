package com.videoai.monitoring.core.support;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

class StreamUrlsTest {
    private static final String PUBLIC = "http://zlm.example:8080";

    @Test
    void streamNameFromSourceExtractsLiveMarker() {
        assertEquals("nvr65", StreamUrls.streamNameFromSource("rtmp://zlm/live/nvr65"));
        assertEquals("cam01", StreamUrls.streamNameFromSource("rtsp://192.168.11.195:8554/live/cam01"));
        assertEquals("cam01", StreamUrls.streamNameFromSource("rtmp://zlm/live/cam01/"));
        assertNull(StreamUrls.streamNameFromSource("rtsp://admin:x@192.168.11.65:554/Streaming/Channels/101"));
        assertNull(StreamUrls.streamNameFromSource("http://example.com/watch"));
    }

    @Test
    void playbackUrlForRtspUsesZlmLiveFlv() {
        assertEquals(PUBLIC + "/live/cam01.live.flv",
                StreamUrls.playbackUrl(PUBLIC, "rtsp://192.168.11.195:8554/stream01", "cam01"));
    }

    @Test
    void playbackUrlForInternalStreamUsesZlmLiveFlv() {
        assertEquals(PUBLIC + "/live/nvr65.live.flv",
                StreamUrls.playbackUrl(PUBLIC, "rtmp://zlm/live/nvr65", "fallback"));
        assertEquals(PUBLIC + "/live/nvr65.live.flv",
                StreamUrls.playbackUrl(PUBLIC, "rtmp://localhost/live/nvr65", "fallback"));
        assertEquals(PUBLIC + "/live/nvr65.live.flv",
                StreamUrls.playbackUrl(PUBLIC, "rtmp://host.docker.internal/live/nvr65", "fallback"));
        assertEquals(PUBLIC + "/live/nvr65.live.flv",
                StreamUrls.playbackUrl(PUBLIC, "rtmp://172.21.0.1/live/nvr65", "fallback"));
    }

    @Test
    void playbackUrlForHttpReturnsSourceAsIs() {
        assertEquals("http://example.com/stream.m3u8",
                StreamUrls.playbackUrl(PUBLIC, "http://example.com/stream.m3u8", "cam01"));
        assertEquals("https://example.com/stream.m3u8",
                StreamUrls.playbackUrl(PUBLIC, "https://example.com/stream.m3u8", "cam01"));
    }

    @Test
    void playbackUrlForExternalRtmpFallsBackToMjpeg() {
        assertEquals("/api/streams/live/foo.mjpeg",
                StreamUrls.playbackUrl(PUBLIC, "rtmp://203.0.113.5/live/foo", "cam01"));
    }

    @Test
    void playbackUrlForOtherSchemesFallsBackToMjpegWithFallbackStream() {
        assertEquals("/api/streams/live/abc-123.mjpeg",
                StreamUrls.playbackUrl(PUBLIC, "srt://example.com/stream", "abc-123"));
    }
}
