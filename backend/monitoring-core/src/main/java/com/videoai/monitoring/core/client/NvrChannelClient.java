package com.videoai.monitoring.core.client;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;
import org.xml.sax.InputSource;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import java.io.StringReader;
import java.net.http.HttpResponse;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * 从 NVR/CVR 读取通道清单（海康 ISAPI，HTTP Digest）。
 * 通道名优先取 StreamingChannel 的 channelName，缺省用 InputProxyChannel 的 name，
 * 再缺省「通道N」；enabled=false 的通道跳过；InputProxy 接口缺失时源 IPC 地址留空。
 * 任何日志/异常消息都不得包含设备密码。
 */
@Component
public class NvrChannelClient {

    private final IsapiDigestClient digestClient;

    public NvrChannelClient() {
        this(new IsapiDigestClient());
    }

    public NvrChannelClient(IsapiDigestClient digestClient) {
        this.digestClient = digestClient;
    }

    /** 一台 NVR/CVR 的读取结果：通道清单 + 设备 RTSP 端口（默认 554）。 */
    public record NvrDevice(List<NvrChannel> channels, int rtspPort) {
    }

    /** 一台 NVR/CVR 的一个摄像头通道：channel 为通道号，trackId 为主码流 ID（如 101）。 */
    public record NvrChannel(int channel, int trackId, String name, String sourceIp) {
    }

    /** StreamingChannel 主流条目（仅保留 id 以 01 结尾的流）。 */
    record StreamChannel(int id, String channelName, boolean enabled) {
    }

    /** InputProxyChannel 条目：通道号、通道名与源 IPC 地址。 */
    record InputProxyChannel(int id, String name, String ip) {
    }

    /**
     * 拉取设备通道列表与 RTSP 端口。凭据错误或设备不可达时抛 ResponseStatusException(BAD_GATEWAY)，
     * 消息不含密码；InputProxy / Network 端口接口不可用（部分固件无此接口）时对应信息留空/取默认，不视为失败。
     * CVR 中心存储（DS-A80348S 等）没有可用的 Streaming/channels（实测 HTTP 403），
     * 此时回退为 InputProxy 通道清单；两者都拿不到才报错。
     */
    public NvrDevice fetchDevice(String host, int port, String username, String password) {
        String base = "http://" + host + ":" + port;
        requireOk(get(base + "/ISAPI/System/deviceInfo", username, password), host, "设备信息读取失败");
        Map<Integer, InputProxyChannel> sourceChannels = fetchInputProxy(base, username, password);
        HttpResponse<String> streaming = get(base + "/ISAPI/Streaming/channels", username, password);
        List<NvrChannel> channels = new ArrayList<>();
        if (streaming.statusCode() == 200) {
            for (StreamChannel stream : parseStreamingChannels(streaming.body())) {
                int channel = stream.id() / 100;
                InputProxyChannel proxy = sourceChannels.get(channel);
                String name = stream.channelName() != null ? stream.channelName()
                        : proxy != null && proxy.name() != null ? proxy.name()
                        : "通道" + channel;
                channels.add(new NvrChannel(channel, stream.id(), name, proxy != null ? proxy.ip() : null));
            }
        }
        if (channels.isEmpty()) {
            channels.addAll(fromInputProxy(sourceChannels));
        }
        if (channels.isEmpty() && streaming.statusCode() != 200) {
            requireOk(streaming, host, "通道列表读取失败");
        }
        return new NvrDevice(channels, fetchRtspPort(base, username, password));
    }

    /**
     * CVR/中心存储回退路径：Streaming/channels 不可用时按 InputProxy 通道清单构造通道，
     * 主码流 trackId = 通道号 * 100 + 1（现场实测 CVR 通道 108 → trackId 10801）。
     */
    static List<NvrChannel> fromInputProxy(Map<Integer, InputProxyChannel> sourceChannels) {
        List<NvrChannel> channels = new ArrayList<>();
        for (Map.Entry<Integer, InputProxyChannel> entry : new TreeMap<>(sourceChannels).entrySet()) {
            int id = entry.getKey();
            InputProxyChannel proxy = entry.getValue();
            channels.add(new NvrChannel(id, id * 100 + 1,
                    proxy.name() != null ? proxy.name() : "通道" + id, proxy.ip()));
        }
        return channels;
    }

    private Map<Integer, InputProxyChannel> fetchInputProxy(String base, String username, String password) {
        try {
            HttpResponse<String> proxy = get(base + "/ISAPI/ContentMgmt/InputProxy/channels", username, password);
            if (proxy.statusCode() == 200) {
                return parseInputProxyChannels(proxy.body());
            }
        } catch (Exception ignored) {
            // InputProxy 不可用不阻塞导入：通道仍可经 NVR 拉流，仅源 IPC 地址留空
        }
        return Map.of();
    }

    /** 设备 RTSP 端口：读 /ISAPI/System/Network/ports，失败时按海康默认 554。 */
    private int fetchRtspPort(String base, String username, String password) {
        try {
            HttpResponse<String> response = get(base + "/ISAPI/System/Network/ports", username, password);
            if (response.statusCode() == 200) {
                Integer rtspPort = parseRtspPort(response.body());
                if (rtspPort != null) {
                    return rtspPort;
                }
            }
        } catch (Exception ignored) {
            // 端口信息是增强属性，读取失败按默认 554
        }
        return 554;
    }

    private HttpResponse<String> get(String url, String username, String password) {
        try {
            return digestClient.get(url, username, password);
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "NVR 连接失败: " + e.getMessage(), e);
        }
    }

    private static void requireOk(HttpResponse<String> response, String host, String action) {
        if (response.statusCode() != 200) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY,
                    "NVR " + host + " " + action + "（HTTP " + response.statusCode() + "），请检查地址与账号密码");
        }
    }

    /** 解析 InputProxyChannel 列表为 通道号 → 通道名/源 IPC 地址。 */
    static Map<Integer, InputProxyChannel> parseInputProxyChannels(String xml) {
        Document root = parseXml(xml);
        Map<Integer, InputProxyChannel> channels = new HashMap<>();
        for (Element item : elements(root, "InputProxyChannel")) {
            Integer id = intChild(item, "id");
            if (id != null) {
                channels.put(id, new InputProxyChannel(id, childText(item, "name"), childText(item, "ipAddress")));
            }
        }
        return channels;
    }

    /** 解析 StreamingChannel 列表，仅保留主码流（id 以 01 结尾）且 enabled 的条目。 */
    static List<StreamChannel> parseStreamingChannels(String xml) {
        Document root = parseXml(xml);
        List<StreamChannel> channels = new ArrayList<>();
        for (Element item : elements(root, "StreamingChannel")) {
            Integer id = intChild(item, "id");
            if (id == null || id % 100 != 1) {
                continue;
            }
            String enabledText = childText(item, "enabled");
            boolean enabled = enabledText == null || Boolean.parseBoolean(enabledText);
            if (enabled) {
                channels.add(new StreamChannel(id, childText(item, "channelName"), true));
            }
        }
        return channels;
    }

    /** 解析 /ISAPI/System/Network/ports 中的 RTSP 端口。 */
    static Integer parseRtspPort(String xml) {
        Document root = parseXml(xml);
        NodeList nodes = root.getElementsByTagNameNS("*", "RTSP");
        for (int i = 0; i < nodes.getLength(); i++) {
            Integer port = intChild((Element) nodes.item(i), "portNo");
            if (port != null) {
                return port;
            }
        }
        return null;
    }

    /** XXE 防护 + 命名空间无关解析（海康各固件 XML 命名空间不一致）。 */
    private static Document parseXml(String xml) {
        try {
            DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
            factory.setNamespaceAware(true);
            factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
            factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
            factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
            factory.setXIncludeAware(false);
            factory.setExpandEntityReferences(false);
            DocumentBuilder builder = factory.newDocumentBuilder();
            return builder.parse(new InputSource(new StringReader(xml.trim())));
        } catch (Exception exception) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "NVR 响应 XML 解析失败: " + exception.getMessage(), exception);
        }
    }

    private static List<Element> elements(Document root, String tag) {
        NodeList nodes = root.getElementsByTagNameNS("*", tag);
        List<Element> result = new ArrayList<>();
        for (int i = 0; i < nodes.getLength(); i++) {
            result.add((Element) nodes.item(i));
        }
        return result;
    }

    private static String childText(Element parent, String tag) {
        NodeList nodes = parent.getElementsByTagNameNS("*", tag);
        if (nodes.getLength() == 0) {
            return null;
        }
        String text = nodes.item(0).getTextContent();
        if (text == null) {
            return null;
        }
        String trimmed = text.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }

    private static Integer intChild(Element parent, String tag) {
        String text = childText(parent, tag);
        if (text == null) {
            return null;
        }
        try {
            return Integer.valueOf(text);
        } catch (NumberFormatException e) {
            return null;
        }
    }
}
