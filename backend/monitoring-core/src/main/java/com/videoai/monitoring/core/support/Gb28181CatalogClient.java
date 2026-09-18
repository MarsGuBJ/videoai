package com.videoai.monitoring.core.support;

import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;
import org.xml.sax.InputSource;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import org.springframework.stereotype.Component;
import java.io.IOException;
import java.io.StringReader;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetSocketAddress;
import java.net.SocketTimeoutException;
import java.nio.charset.Charset;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;

/**
 * GB28181 SIP MESSAGE Catalog 查询客户端（UDP + Digest 鉴权 + MANSCDP XML）。
 * 向级联服务器发送 Catalog 查询，收集对端推送的 Catalog Response（可能分多包，
 * 按 SumNum 累计），超时或收齐后返回设备清单。
 * Digest 计算与 XML 解析拆为包可见静态方法，便于单测。
 */
@Component
public class Gb28181CatalogClient {

    /** 本级 SIP 参数（access_configs 表 gb28181 配置）。 */
    public record LocalSipConfig(String sipId, String sipDomain, String sipIp, String sipPort) {
    }

    /** 级联服务器（gb28181_access_configs 条目）。 */
    public record TargetServer(String sipId, String sipIp, String sipPort, String username, String password) {
    }

    /** Catalog Item 中的设备条目。 */
    public record Gb28181CatalogDevice(String deviceId, String name, String manufacturer, String model,
                                       String owner, String parentId) {
    }

    /** 一页 Catalog Response：SumNum 为设备总数（分页时跨多包累计），items 为本页设备。 */
    public record CatalogPage(int sumNum, List<Gb28181CatalogDevice> items) {
    }

    /** 查询失败（超时/不可达/鉴权失败），message 为可直接展示的中文原因。 */
    public static class CatalogQueryException extends RuntimeException {
        public CatalogQueryException(String message) {
            super(message);
        }

        public CatalogQueryException(String message, Throwable cause) {
            super(message, cause);
        }
    }

    private static final int TOTAL_TIMEOUT_MS = 8000;
    private static final int RECEIVE_TIMEOUT_MS = 1000;
    private static final String USER_AGENT = "VideoAI-Monitoring";
    /** GB28181 信令常用 GB2312；GBK 为其超集且 JDK 必带，ASCII 内容两者一致。 */
    private static final Charset GB_CHARSET = Charset.forName("GBK");

    /**
     * 查询级联服务器设备目录。
     * 先不带鉴权发送 Catalog Query；收到 401 时按 WWW-Authenticate 计算 Digest 后重发一次；
     * 收到对端 MESSAGE（Catalog Response）回 200 OK 并累计 Item，达到 SumNum 或总超时结束。
     */
    public List<Gb28181CatalogDevice> queryCatalog(LocalSipConfig local, TargetServer target) {
        validate(local, target);
        final int targetPort;
        final int localPort;
        try {
            targetPort = Integer.parseInt(target.sipPort().trim());
            localPort = Integer.parseInt(local.sipPort().trim());
        } catch (NumberFormatException exception) {
            throw new CatalogQueryException("SIP 端口配置非法: " + exception.getMessage());
        }
        InetSocketAddress targetAddress = new InetSocketAddress(target.sipIp().trim(), targetPort);
        if (targetAddress.isUnresolved()) {
            throw new CatalogQueryException("级联服务器地址无法解析: " + target.sipIp());
        }
        String requestUri = "sip:" + target.sipId() + "@" + target.sipIp().trim() + ":" + targetPort;
        String callId = randomHex(16) + "@" + local.sipId();
        String fromTag = randomHex(8);
        String branch = "z9hG4bK" + randomHex(12);
        String sn = String.valueOf(ThreadLocalRandom.current().nextInt(100000, 999999));
        String body = "<?xml version=\"1.0\" encoding=\"GB2312\"?>\r\n"
                + "<Query><CmdType>Catalog</CmdType><SN>" + sn + "</SN>"
                + "<DeviceID>" + target.sipId() + "</DeviceID></Query>";

        Map<String, Gb28181CatalogDevice> devices = new LinkedHashMap<>();
        int sumNum = -1;
        boolean challenged = false;
        boolean gotAnyResponse = false;
        long deadline = System.currentTimeMillis() + TOTAL_TIMEOUT_MS;
        try (DatagramSocket socket = new DatagramSocket()) {
            socket.setSoTimeout(RECEIVE_TIMEOUT_MS);
            send(socket, targetAddress, buildQueryMessage(local, target, requestUri, callId, fromTag, branch,
                    localPort, null, body));
            while (System.currentTimeMillis() < deadline) {
                DatagramPacket packet = new DatagramPacket(new byte[65535], 65535);
                try {
                    socket.receive(packet);
                } catch (SocketTimeoutException timeout) {
                    continue;
                }
                String message = new String(packet.getData(), 0, packet.getLength(), GB_CHARSET);
                String startLine = startLine(message);
                if (startLine.startsWith("SIP/2.0")) {
                    gotAnyResponse = true;
                    int code = statusCode(startLine);
                    if ((code == 401 || code == 407) && !challenged) {
                        String challenge = headerValue(message,
                                code == 401 ? "WWW-Authenticate" : "Proxy-Authenticate");
                        if (challenge == null) {
                            throw new CatalogQueryException("级联服务器要求鉴权但未携带 Digest 挑战头");
                        }
                        challenged = true;
                        String authorization = buildDigestAuthorization(challenge, target.username(),
                                target.password(), "MESSAGE", requestUri);
                        branch = "z9hG4bK" + randomHex(12);
                        send(socket, targetAddress, buildQueryMessage(local, target, requestUri, callId, fromTag,
                                branch, localPort, authorization, body));
                    } else if (code == 401 || code == 403 || code == 407) {
                        throw new CatalogQueryException("级联服务器鉴权失败（" + code + "），请检查用户名/密码");
                    }
                    // 查询 MESSAGE 本身的 200 OK 等其它响应：不是 Catalog 数据，继续等待
                } else if (startLine.startsWith("MESSAGE ")) {
                    gotAnyResponse = true;
                    // 对端推送的 Catalog Response：先回 200 OK 再解析
                    send(socket, packet.getSocketAddress() instanceof InetSocketAddress address
                                    ? address : targetAddress,
                            buildOkResponse(message));
                    String responseBody = bodyOf(message);
                    if (responseBody != null && responseBody.contains("<CmdType>Catalog</CmdType>")
                            && responseBody.contains("<Response")) {
                        CatalogPage page = parseCatalogResponse(responseBody);
                        if (page.sumNum() >= 0) {
                            sumNum = page.sumNum();
                        }
                        for (Gb28181CatalogDevice device : page.items()) {
                            if (device.deviceId() != null && !device.deviceId().isBlank()) {
                                devices.put(device.deviceId(), device);
                            }
                        }
                        if (sumNum >= 0 && devices.size() >= sumNum) {
                            return List.copyOf(devices.values());
                        }
                    }
                }
            }
        } catch (CatalogQueryException exception) {
            throw exception;
        } catch (IOException exception) {
            throw new CatalogQueryException("级联服务器不可达: " + exception.getMessage(), exception);
        }
        if (!devices.isEmpty()) {
            // 总超时但已收到部分 Catalog：返回已收集到的设备
            return List.copyOf(devices.values());
        }
        if (!gotAnyResponse) {
            throw new CatalogQueryException(
                    "查询设备目录超时：级联服务器 " + target.sipIp() + ":" + targetPort + " 无响应");
        }
        throw new CatalogQueryException("查询设备目录超时：未收到 Catalog 应答");
    }

    // --- SIP 报文构造 ---

    private static String buildQueryMessage(LocalSipConfig local, TargetServer target, String requestUri,
                                            String callId, String fromTag, String branch, int localPort,
                                            String authorization, String body) {
        StringBuilder message = new StringBuilder();
        message.append("MESSAGE ").append(requestUri).append(" SIP/2.0\r\n");
        message.append("Via: SIP/2.0/UDP ").append(local.sipIp().trim()).append(':').append(localPort)
                .append(";branch=").append(branch).append(";rport\r\n");
        message.append("From: <sip:").append(local.sipId()).append('@').append(local.sipDomain())
                .append(">;tag=").append(fromTag).append("\r\n");
        message.append("To: <sip:").append(target.sipId()).append('@').append(target.sipIp().trim())
                .append(':').append(target.sipPort().trim()).append(">\r\n");
        message.append("Call-ID: ").append(callId).append("\r\n");
        message.append("CSeq: 1 MESSAGE\r\n");
        message.append("Max-Forwards: 70\r\n");
        message.append("User-Agent: ").append(USER_AGENT).append("\r\n");
        message.append("Content-Type: Application/MANSCDP+xml\r\n");
        if (authorization != null) {
            message.append("Authorization: ").append(authorization).append("\r\n");
        }
        byte[] bodyBytes = body.getBytes(GB_CHARSET);
        message.append("Content-Length: ").append(bodyBytes.length).append("\r\n\r\n");
        message.append(body);
        return message.toString();
    }

    /** 对对端 MESSAGE 的 200 OK：Via/From/Call-ID/CSeq 原样回显，To 补 tag。 */
    private static String buildOkResponse(String request) {
        String via = headerValue(request, "Via");
        String from = headerValue(request, "From");
        String to = headerValue(request, "To");
        String callId = headerValue(request, "Call-ID");
        String cseq = headerValue(request, "CSeq");
        if (to != null && !to.contains(";tag=")) {
            to = to + ";tag=" + randomHex(8);
        }
        StringBuilder response = new StringBuilder();
        response.append("SIP/2.0 200 OK\r\n");
        if (via != null) {
            response.append("Via: ").append(via).append("\r\n");
        }
        if (from != null) {
            response.append("From: ").append(from).append("\r\n");
        }
        if (to != null) {
            response.append("To: ").append(to).append("\r\n");
        }
        if (callId != null) {
            response.append("Call-ID: ").append(callId).append("\r\n");
        }
        if (cseq != null) {
            response.append("CSeq: ").append(cseq).append("\r\n");
        }
        response.append("User-Agent: ").append(USER_AGENT).append("\r\n");
        response.append("Content-Length: 0\r\n\r\n");
        return response.toString();
    }

    private static void send(DatagramSocket socket, InetSocketAddress target, String message) throws IOException {
        byte[] bytes = message.getBytes(GB_CHARSET);
        socket.send(new DatagramPacket(bytes, bytes.length, target));
    }

    // --- Digest 鉴权（包可见以便单测） ---

    /** 解析 WWW-Authenticate 头为参数 map（去掉 Digest 前缀与引号）。 */
    static Map<String, String> parseDigestChallenge(String header) {
        Map<String, String> params = new LinkedHashMap<>();
        if (header == null) {
            return params;
        }
        String value = header.trim();
        if (value.regionMatches(true, 0, "Digest", 0, "Digest".length())) {
            value = value.substring("Digest".length()).trim();
        }
        for (String pair : value.split(",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)")) {
            int equals = pair.indexOf('=');
            if (equals < 0) {
                continue;
            }
            String key = pair.substring(0, equals).trim().toLowerCase();
            String raw = pair.substring(equals + 1).trim();
            if (raw.length() >= 2 && raw.startsWith("\"") && raw.endsWith("\"")) {
                raw = raw.substring(1, raw.length() - 1);
            }
            params.put(key, raw);
        }
        return params;
    }

    /**
     * RFC 2617 Digest response：HA1=MD5(user:realm:pass)，HA2=MD5(method:uri)；
     * 无 qop 时 response=MD5(HA1:nonce:HA2)，qop=auth 时按 MD5(HA1:nonce:nc:cnonce:qop:HA2)。
     */
    static String digestResponse(String username, String password, String realm, String nonce,
                                 String qop, String nc, String cnonce, String method, String uri) {
        String ha1 = md5Hex(username + ":" + realm + ":" + password);
        String ha2 = md5Hex(method + ":" + uri);
        if (qop != null && !qop.isBlank()) {
            return md5Hex(ha1 + ":" + nonce + ":" + nc + ":" + cnonce + ":" + qop + ":" + ha2);
        }
        return md5Hex(ha1 + ":" + nonce + ":" + ha2);
    }

    /** 由 WWW-Authenticate 挑战构造 Authorization 头值。 */
    static String buildDigestAuthorization(String challengeHeader, String username, String password,
                                           String method, String uri) {
        Map<String, String> challenge = parseDigestChallenge(challengeHeader);
        String realm = challenge.get("realm");
        String nonce = challenge.get("nonce");
        if (realm == null || nonce == null) {
            throw new CatalogQueryException("级联服务器 Digest 挑战缺少 realm/nonce");
        }
        String qop = challenge.get("qop");
        if (qop != null && qop.contains("auth")) {
            qop = "auth";
        } else {
            qop = null;
        }
        String nc = "00000001";
        String cnonce = randomHex(8);
        String response = digestResponse(username, password != null ? password : "", realm, nonce,
                qop, nc, cnonce, method, uri);
        StringBuilder authorization = new StringBuilder("Digest ");
        authorization.append("username=\"").append(username).append("\", ");
        authorization.append("realm=\"").append(realm).append("\", ");
        authorization.append("nonce=\"").append(nonce).append("\", ");
        authorization.append("uri=\"").append(uri).append("\", ");
        authorization.append("response=\"").append(response).append("\"");
        if (qop != null) {
            authorization.append(", qop=").append(qop).append(", nc=").append(nc)
                    .append(", cnonce=\"").append(cnonce).append("\"");
        }
        String algorithm = challenge.get("algorithm");
        if (algorithm != null) {
            authorization.append(", algorithm=").append(algorithm);
        }
        return authorization.toString();
    }

    static String md5Hex(String text) {
        try {
            MessageDigest digest = MessageDigest.getInstance("MD5");
            byte[] hash = digest.digest(text.getBytes(GB_CHARSET));
            StringBuilder hex = new StringBuilder(hash.length * 2);
            for (byte b : hash) {
                hex.append(Character.forDigit((b >> 4) & 0xF, 16));
                hex.append(Character.forDigit(b & 0xF, 16));
            }
            return hex.toString();
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("MD5 不可用", exception);
        }
    }

    // --- MANSCDP XML 解析（包可见以便单测） ---

    /** 解析一页 Catalog Response：提取 SumNum 与 DeviceList 下的全部 Item。 */
    static CatalogPage parseCatalogResponse(String xml) {
        Document document = parseXml(xml);
        Element root = document.getDocumentElement();
        int sumNum = -1;
        NodeList sumNodes = root.getElementsByTagName("SumNum");
        if (sumNodes.getLength() > 0) {
            try {
                sumNum = Integer.parseInt(sumNodes.item(0).getTextContent().trim());
            } catch (NumberFormatException ignored) {
                sumNum = -1;
            }
        }
        List<Gb28181CatalogDevice> items = new ArrayList<>();
        NodeList itemNodes = root.getElementsByTagName("Item");
        for (int i = 0; i < itemNodes.getLength(); i++) {
            Element item = (Element) itemNodes.item(i);
            items.add(new Gb28181CatalogDevice(
                    childText(item, "DeviceID"),
                    childText(item, "Name"),
                    childText(item, "Manufacturer"),
                    childText(item, "Model"),
                    childText(item, "Owner"),
                    childText(item, "ParentId")));
        }
        return new CatalogPage(sumNum, items);
    }

    /** XXE 防护：禁用 DOCTYPE 与外部实体。 */
    private static Document parseXml(String xml) {
        try {
            DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
            factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
            factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
            factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
            factory.setXIncludeAware(false);
            factory.setExpandEntityReferences(false);
            DocumentBuilder builder = factory.newDocumentBuilder();
            return builder.parse(new InputSource(new StringReader(xml.trim())));
        } catch (Exception exception) {
            throw new CatalogQueryException("Catalog 响应 XML 解析失败: " + exception.getMessage(), exception);
        }
    }

    private static String childText(Element parent, String tag) {
        NodeList nodes = parent.getElementsByTagName(tag);
        if (nodes.getLength() == 0) {
            return null;
        }
        String text = nodes.item(0).getTextContent();
        return text != null ? text.trim() : null;
    }

    // --- 报文工具 ---

    private static String startLine(String message) {
        int end = message.indexOf("\r\n");
        return end < 0 ? message.trim() : message.substring(0, end).trim();
    }

    private static int statusCode(String startLine) {
        String[] parts = startLine.split(" ");
        if (parts.length < 2) {
            return -1;
        }
        try {
            return Integer.parseInt(parts[1]);
        } catch (NumberFormatException exception) {
            return -1;
        }
    }

    private static String headerValue(String message, String name) {
        for (String line : message.split("\r\n")) {
            int colon = line.indexOf(':');
            if (colon > 0 && line.substring(0, colon).trim().equalsIgnoreCase(name)) {
                return line.substring(colon + 1).trim();
            }
        }
        return null;
    }

    private static String bodyOf(String message) {
        int separator = message.indexOf("\r\n\r\n");
        return separator < 0 ? null : message.substring(separator + 4);
    }

    private static String randomHex(int length) {
        StringBuilder hex = new StringBuilder(length);
        ThreadLocalRandom random = ThreadLocalRandom.current();
        for (int i = 0; i < length; i++) {
            hex.append(Character.forDigit(random.nextInt(16), 16));
        }
        return hex.toString();
    }

    private static void validate(LocalSipConfig local, TargetServer target) {
        if (local == null || isBlank(local.sipId()) || isBlank(local.sipDomain())
                || isBlank(local.sipIp()) || isBlank(local.sipPort())) {
            throw new CatalogQueryException("本级 GB28181 SIP 参数不完整（sipId/sipDomain/sipIp/sipPort）");
        }
        if (target == null || isBlank(target.sipId()) || isBlank(target.sipIp()) || isBlank(target.sipPort())) {
            throw new CatalogQueryException("级联服务器 SIP 参数不完整（sipId/sipIp/sipPort）");
        }
    }

    private static boolean isBlank(String value) {
        return value == null || value.isBlank();
    }
}
