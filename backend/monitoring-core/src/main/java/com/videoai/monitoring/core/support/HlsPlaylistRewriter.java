package com.videoai.monitoring.core.support;

/**
 * HLS playlist rewriting ported from backend-lite/main.py rewrite_hls_playlist / rewrite_hls_uri:
 * non-comment lines are rewritten to /api/streams/{app}/{segment} pointing back at this service.
 */
public final class HlsPlaylistRewriter {

    private HlsPlaylistRewriter() {
    }

    public static String rewrite(String playlist, String streamApp) {
        String[] lines = playlist.split("\n", -1);
        StringBuilder result = new StringBuilder(playlist.length() + 64);
        for (int index = 0; index < lines.length; index++) {
            String rawLine = lines[index];
            String line = rawLine.strip();
            if (line.isEmpty() || line.startsWith("#")) {
                result.append(rawLine);
            } else {
                result.append(rewriteUri(line, streamApp));
            }
            if (index < lines.length - 1) {
                result.append('\n');
            }
        }
        return result.toString();
    }

    static String rewriteUri(String uri, String streamApp) {
        String path = uri;
        String query = null;
        int queryIndex = uri.indexOf('?');
        if (queryIndex >= 0) {
            path = uri.substring(0, queryIndex);
            query = uri.substring(queryIndex + 1);
        }
        String app;
        String name;
        if (path.startsWith("/")) {
            String stripped = path.replaceAll("^/+|/+$", "");
            String[] parts = stripped.split("/", 2);
            app = parts.length > 0 && !parts[0].isEmpty() ? parts[0] : streamApp;
            name = parts.length > 1 ? parts[1] : "";
        } else {
            app = streamApp;
            name = path;
        }
        String rewritten = "/api/streams/" + StreamUrls.quote(app) + "/" + StreamUrls.quote(name);
        return query != null && !query.isEmpty() ? rewritten + "?" + query : rewritten;
    }
}
