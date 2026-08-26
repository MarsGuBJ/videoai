package com.videoai.monitoring.core.client;

import org.springframework.stereotype.Component;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Minimal HTTP Digest (RFC 7616, MD5, qop=auth) client for Hikvision ISAPI,
 * ported from the requests.HTTPDigestAuth flow used in backend-lite/main.py.
 */
@Component
public class DigestHttpClient {
    private final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(5))
            .build();
    private final SecureRandom random = new SecureRandom();

    /** Sends the request without auth; on a 401 Digest challenge, answers it and retries. */
    public HttpResponse<byte[]> sendWithDigest(String method, String url, String username, String password,
                                               String body, Duration timeout) throws IOException, InterruptedException {
        HttpResponse<byte[]> response = send(method, url, body, null, timeout);
        if (response.statusCode() != 401) {
            return response;
        }
        String challenge = response.headers().firstValue("WWW-Authenticate").orElse("");
        if (!challenge.regionMatches(true, 0, "Digest", 0, "Digest".length())) {
            return response;
        }
        String authorization = buildAuthorization(challenge, method, url, username, password);
        return send(method, url, body, authorization, timeout);
    }

    public HttpResponse<byte[]> sendWithBasic(String method, String url, String username, String password,
                                              String body, Duration timeout) throws IOException, InterruptedException {
        String token = java.util.Base64.getEncoder()
                .encodeToString((username + ":" + password).getBytes(StandardCharsets.UTF_8));
        return send(method, url, body, "Basic " + token, timeout);
    }

    private HttpResponse<byte[]> send(String method, String url, String body, String authorization,
                                      Duration timeout) throws IOException, InterruptedException {
        HttpRequest.Builder builder = HttpRequest.newBuilder(URI.create(url)).timeout(timeout);
        if (authorization != null) {
            builder.header("Authorization", authorization);
        }
        if (body != null && !body.isEmpty()) {
            builder.header("Content-Type", "application/xml");
            builder.method(method, HttpRequest.BodyPublishers.ofByteArray(body.getBytes(StandardCharsets.UTF_8)));
        } else {
            builder.method(method, HttpRequest.BodyPublishers.noBody());
        }
        return httpClient.send(builder.build(), HttpResponse.BodyHandlers.ofByteArray());
    }

    private String buildAuthorization(String challenge, String method, String url, String username, String password) {
        Map<String, String> params = parseChallenge(challenge);
        String realm = params.getOrDefault("realm", "");
        String nonce = params.getOrDefault("nonce", "");
        String opaque = params.get("opaque");
        String qop = params.get("qop");

        URI uri = URI.create(url);
        String digestUri = uri.getRawPath() + (uri.getRawQuery() != null ? "?" + uri.getRawQuery() : "");

        String ha1 = md5Hex(username + ":" + realm + ":" + password);
        String ha2 = md5Hex(method.toUpperCase() + ":" + digestUri);

        Map<String, String> authParams = new LinkedHashMap<>();
        authParams.put("username", username);
        authParams.put("realm", realm);
        authParams.put("nonce", nonce);
        authParams.put("uri", digestUri);

        String responseDigest;
        if (qop != null && !qop.isBlank()) {
            String selectedQop = "auth";
            String nc = "00000001";
            String cnonce = randomHex(16);
            responseDigest = md5Hex(ha1 + ":" + nonce + ":" + nc + ":" + cnonce + ":" + selectedQop + ":" + ha2);
            authParams.put("qop", selectedQop);
            authParams.put("nc", nc);
            authParams.put("cnonce", cnonce);
        } else {
            responseDigest = md5Hex(ha1 + ":" + nonce + ":" + ha2);
        }
        authParams.put("response", responseDigest);
        if (opaque != null) {
            authParams.put("opaque", opaque);
        }

        StringBuilder header = new StringBuilder("Digest ");
        boolean first = true;
        for (Map.Entry<String, String> entry : authParams.entrySet()) {
            if (!first) {
                header.append(", ");
            }
            first = false;
            header.append(entry.getKey()).append('=');
            if ("nc".equals(entry.getKey()) || "qop".equals(entry.getKey())) {
                header.append(entry.getValue());
            } else {
                header.append('"').append(entry.getValue()).append('"');
            }
        }
        return header.toString();
    }

    private Map<String, String> parseChallenge(String challenge) {
        Map<String, String> params = new LinkedHashMap<>();
        String rest = challenge.substring("Digest".length()).trim();
        for (String part : rest.split(",")) {
            int equals = part.indexOf('=');
            if (equals < 0) {
                continue;
            }
            String key = part.substring(0, equals).trim();
            String value = part.substring(equals + 1).trim();
            if (value.length() >= 2 && value.startsWith("\"") && value.endsWith("\"")) {
                value = value.substring(1, value.length() - 1);
            }
            params.put(key, value);
        }
        return params;
    }

    private String randomHex(int length) {
        StringBuilder builder = new StringBuilder(length);
        String hex = "0123456789abcdef";
        for (int index = 0; index < length; index++) {
            builder.append(hex.charAt(random.nextInt(hex.length())));
        }
        return builder.toString();
    }

    static String md5Hex(String input) {
        try {
            MessageDigest digest = MessageDigest.getInstance("MD5");
            byte[] hash = digest.digest(input.getBytes(StandardCharsets.UTF_8));
            StringBuilder builder = new StringBuilder(hash.length * 2);
            for (byte value : hash) {
                builder.append(String.format("%02x", value));
            }
            return builder.toString();
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("MD5 not available", exception);
        }
    }
}
