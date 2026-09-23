package com.videoai.monitoring.core.service.impl;

import com.videoai.monitoring.common.dto.CameraCreateRequest;
import com.videoai.monitoring.common.dto.CameraUpdateRequest;
import com.videoai.monitoring.common.dto.NvrImportItem;
import com.videoai.monitoring.common.dto.NvrImportPrecheckRequest;
import com.videoai.monitoring.common.dto.NvrImportSyncRequest;
import com.videoai.monitoring.common.vo.CameraResponse;
import com.videoai.monitoring.common.vo.CloudSyncResultResponse;
import com.videoai.monitoring.common.vo.NvrImportFailure;
import com.videoai.monitoring.common.vo.NvrImportPrecheckResponse;
import com.videoai.monitoring.core.client.NvrChannelClient;
import com.videoai.monitoring.core.client.NvrChannelClient.NvrChannel;
import com.videoai.monitoring.core.client.NvrChannelClient.NvrDevice;
import com.videoai.monitoring.core.service.CameraService;
import com.videoai.monitoring.core.service.NvrImportService;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * 从 NVR/CVR 导入设备：通过海康 ISAPI 读取通道清单，按 IP 判重后创建/更新摄像头。
 * 安全约束：任何日志/异常消息不得包含设备密码；sourceUrl 内嵌凭据是设备表现有存储约定。
 */
@Service
public class NvrImportServiceImpl implements NvrImportService {

    private static final String PROTOCOL_RTSP = "RTSP 拉流";
    private static final String STREAM_TYPE_MAIN = "主码流";
    private static final String VENDOR_HIKVISION = "海康威视";

    private final NvrChannelClient nvrChannelClient;
    private final CameraService cameraService;

    public NvrImportServiceImpl(NvrChannelClient nvrChannelClient, CameraService cameraService) {
        this.nvrChannelClient = nvrChannelClient;
        this.cameraService = cameraService;
    }

    @Override
    public NvrImportPrecheckResponse precheck(NvrImportPrecheckRequest request) {
        String username = request.username().trim();
        String password = request.password();
        Map<String, CameraResponse> localByIp = localByIp();
        List<NvrImportItem> items = new ArrayList<>();
        List<NvrImportFailure> failures = new ArrayList<>();
        LinkedHashSet<String> seen = new LinkedHashSet<>();
        for (String entry : request.hosts()) {
            String raw = clean(entry);
            if (raw == null || !seen.add(raw)) {
                continue;
            }
            HostPort target = parseHostPort(raw);
            try {
                NvrDevice device = nvrChannelClient.fetchDevice(target.host(), target.port(), username, password);
                for (NvrChannel channel : device.channels()) {
                    items.add(toItem(channel, target.host(), device.rtspPort(), username, password, localByIp));
                }
            } catch (ResponseStatusException e) {
                failures.add(new NvrImportFailure(target.host(),
                        e.getReason() != null ? e.getReason() : "读取失败"));
            }
        }
        int newCount = (int) items.stream().filter(item -> "new".equals(item.status())).count();
        int updateCount = (int) items.stream().filter(item -> "update".equals(item.status())).count();
        return new NvrImportPrecheckResponse(items, newCount, updateCount, failures);
    }

    @Override
    @Transactional
    public CloudSyncResultResponse sync(NvrImportSyncRequest request) {
        List<NvrImportItem> items = request.items() != null ? request.items() : List.of();
        String targetArea = clean(request.targetArea());
        String username = request.username().trim();
        String password = request.password();
        Map<String, CameraResponse> localByIp = localByIp();
        int created = 0;
        int updated = 0;
        int skipped = 0;
        for (NvrImportItem item : items) {
            String ip = clean(item.ip());
            CameraResponse local = ip != null ? localByIp.get(ip) : null;
            if (local == null) {
                String sourceUrl = clean(item.sourceUrl());
                if (sourceUrl == null) {
                    skipped++;
                    continue;
                }
                String name = clean(item.name()) != null ? item.name().trim()
                        : ip != null ? ip : "通道" + item.channel();
                cameraService.create(new CameraCreateRequest(
                        name, sourceUrl, null, targetArea, null,
                        clean(item.channel()), clean(item.trackId()), STREAM_TYPE_MAIN, PROTOCOL_RTSP, VENDOR_HIKVISION,
                        ip, clean(item.port()), username, password, null, null,
                        null, null, null, null, null, null,
                        null, null, null, null, null, null, null, null));
                created++;
            } else if (request.overwrite()) {
                cameraService.update(local.id(), new CameraUpdateRequest(
                        clean(item.name()), clean(item.sourceUrl()), null, targetArea, null,
                        clean(item.channel()), clean(item.trackId()), STREAM_TYPE_MAIN, PROTOCOL_RTSP, VENDOR_HIKVISION,
                        ip, clean(item.port()), username, password, null, null,
                        null, null, null, null, null, null,
                        null, null, null, null, null, null, null, null));
                updated++;
            } else {
                skipped++;
            }
        }
        return new CloudSyncResultResponse(created, updated, skipped);
    }

    private NvrImportItem toItem(NvrChannel channel, String nvrHost, int rtspPort,
                                 String username, String password, Map<String, CameraResponse> localByIp) {
        String sourceUrl = "rtsp://" + percentEncode(username) + ":" + percentEncode(password)
                + "@" + nvrHost + ":" + rtspPort + "/Streaming/Channels/" + channel.trackId();
        String ip = clean(channel.sourceIp());
        CameraResponse local = ip != null ? localByIp.get(ip) : null;
        return new NvrImportItem(
                channel.name(),
                ip,
                String.valueOf(rtspPort),
                String.valueOf(channel.channel()),
                String.valueOf(channel.trackId()),
                nvrHost,
                sourceUrl,
                PROTOCOL_RTSP,
                local == null ? "new" : "update",
                local == null ? null : local.id().toString());
    }

    private Map<String, CameraResponse> localByIp() {
        return cameraService.list().stream()
                .filter(camera -> camera.ip() != null && !camera.ip().isBlank())
                .collect(Collectors.toMap(CameraResponse::ip, Function.identity(), (a, b) -> a, LinkedHashMap::new));
    }

    /** 解析 "IP" 或 "IP:端口"（端口默认 80）。public 静态以便测试直接覆盖。 */
    public static HostPort parseHostPort(String entry) {
        String value = entry.trim();
        int colon = value.lastIndexOf(':');
        if (colon < 0) {
            return new HostPort(value, 80);
        }
        String host = value.substring(0, colon).trim();
        String portText = value.substring(colon + 1).trim();
        int port;
        try {
            port = Integer.parseInt(portText);
        } catch (NumberFormatException e) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "NVR 地址格式不正确: " + entry);
        }
        if (host.isEmpty() || host.contains("/") || port < 1 || port > 65535) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "NVR 地址格式不正确: " + entry);
        }
        return new HostPort(host, port);
    }

    public record HostPort(String host, int port) {
    }

    /** userinfo 段百分号编码：仅保留非保留字符，其余按 UTF-8 字节 %XX 编码。 */
    static String percentEncode(String value) {
        StringBuilder sb = new StringBuilder(value.length());
        for (byte b : value.getBytes(StandardCharsets.UTF_8)) {
            char c = (char) (b & 0xFF);
            if ((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9')
                    || c == '-' || c == '.' || c == '_' || c == '~') {
                sb.append(c);
            } else {
                sb.append('%').append(String.format("%02X", b));
            }
        }
        return sb.toString();
    }

    private static String clean(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }
}
