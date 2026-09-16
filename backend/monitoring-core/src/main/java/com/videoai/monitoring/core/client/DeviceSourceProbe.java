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
import java.util.Optional;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 按拉流地址探测设备源：从 rtsp://user:pass@host/... 解析主机与凭据，
 * 请求海康 ISAPI 接口回取设备序列号并探测云台能力。
 * 海康设备为 HTTP Digest 认证；java.net.http 的 Authenticator 对部分海康固件
 * 不会触发 Digest 重试（实测 401 后不回 consult Authenticator），故这里手工实现
 * Digest 握手（401 解析 challenge → MD5 计算 response → 带 Authorization 重发）。
 * 仅做单向读取，任何失败都不抛异常，不影响设备创建/编辑主流程。
 */
public class DeviceSourceProbe {

    private static final Pattern SERIAL_PATTERN = Pattern.compile("<serialNumber>([^<]+)</serialNumber>");
    private static final Duration TIMEOUT = Duration.ofSeconds(4);
    private static final SecureRandom RANDOM = new SecureRandom();

    /** 拉流地址可解析出主机与内嵌凭据时才值得尝试探测。 */
    public static boolean isResolvable(String sourceUrl) {
        return parseTarget(sourceUrl) != null;
    }

    /** 仅回取设备序列号（设备创建后后台调用）。 */
    public Optional<String> resolveSerialNumber(String sourceUrl) {
        Target target = parseTarget(sourceUrl);
        if (target == null) {
            return Optional.empty();
        }
        try {
            HttpResponse<String> response = httpGet(client(), "http://" + target.host() + "/ISAPI/System/deviceInfo", target);
            if (response.statusCode() != 200) {
                return Optional.empty();
            }
            return parseSerialNumber(response.body());
        } catch (Exception e) {
            return Optional.empty();
        }
    }

    /**
     * 完整探测：先取 deviceInfo 确认可达并解析序列号，再请求 PTZ 能力接口判断云台支持。
     * 设备不可达时 reachable=false，serialNumber/ptzSupported 均为 null。
     */
    public ProbeResult probe(String sourceUrl) {
        Target target = parseTarget(sourceUrl);
        if (target == null) {
            return new ProbeResult(false, null, null);
        }
        try {
            HttpClient client = client();
            HttpResponse<String> info = httpGet(client, "http://" + target.host() + "/ISAPI/System/deviceInfo", target);
            if (info.statusCode() != 200) {
                return new ProbeResult(false, null, null);
            }
            String serial = parseSerialNumber(info.body()).orElse(null);
            boolean ptz;
            try {
                // 海康云台能力接口：200 表示设备支持云台控制
                ptz = httpGet(client, "http://" + target.host() + "/ISAPI/PTZCtrl/channels/1/capabilities", target).statusCode() == 200;
            } catch (Exception e) {
                ptz = false;
            }
            return new ProbeResult(true, serial, ptz);
        } catch (Exception e) {
            return new ProbeResult(false, null, null);
        }
    }

    public static Optional<String> parseSerialNumber(String xml) {
        if (xml == null) {
            return Optional.empty();
        }
        Matcher matcher = SERIAL_PATTERN.matcher(xml);
        if (!matcher.find()) {
            return Optional.empty();
        }
        String serial = matcher.group(1).trim();
        return serial.isEmpty() ? Optional.empty() : Optional.of(serial);
    }

    /** 解析拉流地址中的连接要素；端口缺省时按协议取默认（rtsp=554、rtmp=1935、http=80、https=443）。 */
    public static ParsedSource parseSource(String sourceUrl) {
        if (sourceUrl == null || sourceUrl.isBlank()) {
            return null;
        }
        try {
            URI uri = URI.create(sourceUrl.trim());
            String host = uri.getHost();
            if (host == null) {
                return null;
            }
            String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase();
            int port = uri.getPort();
            if (port < 0) {
                port = switch (scheme) {
                    case "rtsp" -> 554;
                    case "rtmp" -> 1935;
                    case "http" -> 80;
                    case "https" -> 443;
                    default -> -1;
                };
            }
            String username = null;
            String password = null;
            String userInfo = uri.getUserInfo();
            if (userInfo != null) {
                int sep = userInfo.indexOf(':');
                if (sep > 0) {
                    username = percentDecode(userInfo.substring(0, sep));
                    password = percentDecode(userInfo.substring(sep + 1));
                } else {
                    username = percentDecode(userInfo);
                }
            }
            return new ParsedSource(host, port > 0 ? port : null, username, password);
        } catch (IllegalArgumentException e) {
            return null;
        }
    }

    /** userinfo 段按 %XX 百分号解码；'+' 是合法字面量（非空格），不能用 URLDecoder。 */
    private static String percentDecode(String value) {
        if (value.indexOf('%') < 0) {
            return value;
        }
        StringBuilder sb = new StringBuilder(value.length());
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (c == '%' && i + 2 <= value.length() - 1) {
                try {
                    sb.append((char) Integer.parseInt(value.substring(i + 1, i + 3), 16));
                    i += 2;
                    continue;
                } catch (NumberFormatException ignored) {
                    // 非法转义按原样保留
                }
            }
            sb.append(c);
        }
        return sb.toString();
    }

    private static HttpClient client() {
        return HttpClient.newBuilder().connectTimeout(TIMEOUT).build();
    }

    /** GET 请求；401 Digest challenge 时手工计算摘要并重发一次。 */
    private static HttpResponse<String> httpGet(HttpClient client, String url, Target target) throws Exception {
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
        String ha1 = md5Hex(target.username() + ":" + realm + ":" + target.password());
        String ha2 = md5Hex("GET:" + path);
        String digest = md5Hex(ha1 + ":" + nonce + ":00000001:" + cnonce + ":" + qop + ":" + ha2);
        String authorization = "Digest username=\"" + target.username() + "\", realm=\"" + realm
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

    private static Target parseTarget(String sourceUrl) {
        ParsedSource parsed = parseSource(sourceUrl);
        if (parsed == null || parsed.username() == null || parsed.password() == null || parsed.password().isEmpty()) {
            return null;
        }
        return new Target(parsed.host(), parsed.username(), parsed.password());
    }

    private record Target(String host, String username, String password) {
    }

    public record ParsedSource(String host, Integer port, String username, String password) {
    }

    public record ProbeResult(boolean reachable, String serialNumber, Boolean ptzSupported) {
    }
}
