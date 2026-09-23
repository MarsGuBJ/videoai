package com.videoai.monitoring.core.client;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

/**
 * 海康 ISAPI HTTP Digest 认证 GET 客户端。
 * java.net.http 的 Authenticator 对部分海康固件不会触发 Digest 重试
 * （实测 401 后不回 consult Authenticator），故这里手工实现 Digest 握手
 * （401 解析 challenge → MD5 计算 response → 带 Authorization 重发一次）。
 * 仅做单向读取；调用方自行判断响应状态码。任何日志/异常消息不得包含密码。
 */
public class IsapiDigestClient {

    private static final Duration TIMEOUT = Duration.ofSeconds(4);
    private static final SecureRandom RANDOM = new SecureRandom();

    private final HttpClient client = HttpClient.newBuilder().connectTimeout(TIMEOUT).build();

    /** GET 请求；401 Digest challenge 时手工计算摘要并重发一次，返回最终响应。 */
    public HttpResponse<String> get(String url, String username, String password) throws Exception {
        HttpResponse<String> response = client.send(get(url), HttpResponse.BodyHandlers.ofString());
        if (response.statusCode() != 401) {
            return response;
        }
        String challenge = response.headers().firstValue("WWW-Authenticate").orElse("");
        if (!challenge.regionMatches(true, 0, "Digest", 0, "Digest".length())) {
            return response;
        }
        Map<String, String> params = parseDigestChallenge(challenge);
        String realm = params.get("realm");
        String nonce = params.get("nonce");
        if (realm == null || nonce == null) {
            return response;
        }
        String qop = params.getOrDefault("qop", "auth");
        String path = URI.create(url).getRawPath();
        String cnonce = String.format("%08x", RANDOM.nextInt());
        String ha1 = md5Hex(username + ":" + realm + ":" + password);
        String ha2 = md5Hex("GET:" + path);
        String digest = md5Hex(ha1 + ":" + nonce + ":00000001:" + cnonce + ":" + qop + ":" + ha2);
        String authorization = "Digest username=\"" + username + "\", realm=\"" + realm
                + "\", nonce=\"" + nonce + "\", uri=\"" + path + "\", response=\"" + digest
                + "\", qop=" + qop + ", nc=00000001, cnonce=\"" + cnonce + "\"";
        HttpRequest retry = HttpRequest.newBuilder(URI.create(url)).timeout(TIMEOUT)
                .header("Authorization", authorization).GET().build();
        return client.send(retry, HttpResponse.BodyHandlers.ofString());
    }

    private static HttpRequest get(String url) {
        return HttpRequest.newBuilder(URI.create(url)).timeout(TIMEOUT).GET().build();
    }

    private static Map<String, String> parseDigestChallenge(String header) {
        Map<String, String> params = new HashMap<>();
        String rest = header.substring("Digest".length()).trim();
        // 逗号分隔但忽略引号内的逗号
        for (String part : rest.split(",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)")) {
            int eq = part.indexOf('=');
            if (eq < 0) {
                continue;
            }
            String key = part.substring(0, eq).trim();
            String value = part.substring(eq + 1).trim();
            if (value.startsWith("\"") && value.endsWith("\"") && value.length() >= 2) {
                value = value.substring(1, value.length() - 1);
            }
            params.put(key, value);
        }
        return params;
    }

    private static String md5Hex(String value) throws Exception {
        byte[] digest = MessageDigest.getInstance("MD5").digest(value.getBytes("ISO-8859-1"));
        StringBuilder sb = new StringBuilder(digest.length * 2);
        for (byte b : digest) {
            sb.append(Character.forDigit((b >> 4) & 0xF, 16));
            sb.append(Character.forDigit(b & 0xF, 16));
        }
        return sb.toString();
    }
}
