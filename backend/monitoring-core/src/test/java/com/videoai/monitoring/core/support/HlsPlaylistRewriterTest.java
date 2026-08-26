package com.videoai.monitoring.core.support;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class HlsPlaylistRewriterTest {

    @Test
    void rewritesRelativeSegmentsToLocalApi() {
        String playlist = "#EXTM3U\n"
                + "#EXT-X-VERSION:3\n"
                + "#EXTINF:2.000,\n"
                + "seg-1.ts\n"
                + "seg-2.ts\n";
        String expected = "#EXTM3U\n"
                + "#EXT-X-VERSION:3\n"
                + "#EXTINF:2.000,\n"
                + "/api/streams/live/seg-1.ts\n"
                + "/api/streams/live/seg-2.ts\n";
        assertEquals(expected, HlsPlaylistRewriter.rewrite(playlist, "live"));
    }

    @Test
    void rewritesAbsolutePathSegmentsUsingTheirOwnApp() {
        String playlist = "#EXTM3U\n/live/seg-1.ts";
        assertEquals("#EXTM3U\n/api/streams/live/seg-1.ts",
                HlsPlaylistRewriter.rewrite(playlist, "live"));
    }

    @Test
    void keepsQueryStringOnSegments() {
        String playlist = "#EXTM3U\nseg-1.ts?vhost=__defaultVhost__";
        assertEquals("#EXTM3U\n/api/streams/live/seg-1.ts?vhost=__defaultVhost__",
                HlsPlaylistRewriter.rewrite(playlist, "live"));
    }

    @Test
    void keepsCommentsAndBlankLinesUntouched() {
        String playlist = "#EXTM3U\r\n#EXT-X-ENDLIST\r\n";
        assertEquals("#EXTM3U\r\n#EXT-X-ENDLIST\r\n",
                HlsPlaylistRewriter.rewrite(playlist, "live"));
    }

    @Test
    void handlesPlaylistWithoutTrailingNewline() {
        String playlist = "#EXTM3U\nseg-1.ts";
        assertEquals("#EXTM3U\n/api/streams/live/seg-1.ts",
                HlsPlaylistRewriter.rewrite(playlist, "live"));
    }
}
