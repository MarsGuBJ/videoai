package com.videoai.monitoring.core.service.impl;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.videoai.monitoring.common.dto.CameraCreateRequest;
import com.videoai.monitoring.common.dto.CameraUpdateRequest;
import com.videoai.monitoring.common.dto.CloudDeviceItem;
import com.videoai.monitoring.common.dto.CloudPlatformCreateRequest;
import com.videoai.monitoring.common.dto.CloudPlatformUpdateRequest;
import com.videoai.monitoring.common.dto.CloudSyncRequest;
import com.videoai.monitoring.common.vo.CameraResponse;
import com.videoai.monitoring.common.vo.CloudPlatformResponse;
import com.videoai.monitoring.common.vo.CloudSyncPrecheckResponse;
import com.videoai.monitoring.common.vo.CloudSyncResultResponse;
import com.videoai.monitoring.core.dao.CloudPlatformDao;
import com.videoai.monitoring.core.entity.CloudPlatformEntity;
import com.videoai.monitoring.core.service.CameraService;
import com.videoai.monitoring.core.service.CloudPlatformService;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
public class CloudPlatformServiceImpl implements CloudPlatformService {
    private final CloudPlatformDao cloudPlatformDao;
    private final CameraService cameraService;
    private final ObjectMapper objectMapper;
    private final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build();

    public CloudPlatformServiceImpl(CloudPlatformDao cloudPlatformDao, CameraService cameraService,
                                    ObjectMapper objectMapper) {
        this.cloudPlatformDao = cloudPlatformDao;
        this.cameraService = cameraService;
        this.objectMapper = objectMapper;
    }

    @Override
    public List<CloudPlatformResponse> list() {
        return cloudPlatformDao.selectAllOrdered().stream().map(this::toResponse).toList();
    }

    @Override
    public CloudPlatformResponse get(UUID id) {
        return find(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Cloud platform not found"));
    }

    @Override
    public Optional<CloudPlatformResponse> find(UUID id) {
        return Optional.ofNullable(cloudPlatformDao.selectById(id)).map(this::toResponse);
    }

    @Override
    @Transactional
    public CloudPlatformResponse create(CloudPlatformCreateRequest request) {
        UUID id = UUID.randomUUID();
        CloudPlatformEntity entity = new CloudPlatformEntity();
        entity.setId(id);
        entity.setName(request.name());
        entity.setType(request.type());
        entity.setKey(request.key());
        entity.setSecret(request.secret());
        entity.setIp(request.ip());
        entity.setPort(request.port());
        cloudPlatformDao.insert(entity);
        return get(id);
    }

    @Override
    @Transactional
    public CloudPlatformResponse update(UUID id, CloudPlatformUpdateRequest request) {
        get(id);
        CloudPlatformEntity entity = new CloudPlatformEntity();
        entity.setId(id);
        entity.setName(request.name());
        entity.setType(request.type());
        entity.setKey(request.key());
        entity.setSecret(request.secret());
        entity.setIp(request.ip());
        entity.setPort(request.port());
        cloudPlatformDao.updateCloudPlatform(entity);
        return get(id);
    }

    @Override
    @Transactional
    public void delete(UUID id) {
        find(id).ifPresent(platform -> cloudPlatformDao.deleteById(id));
    }

    @Override
    public CloudSyncPrecheckResponse precheck(UUID id) {
        CloudPlatformEntity platform = requireEntity(id);
        List<CloudDeviceItem> cloudDevices = fetchCloudDevices(platform);
        List<CloudDeviceItem> items = diffByIp(cloudDevices, cameraService.list());
        int newCount = (int) items.stream().filter(item -> "new".equals(item.status())).count();
        int updateCount = (int) items.stream().filter(item -> "update".equals(item.status())).count();
        return new CloudSyncPrecheckResponse(items, newCount, updateCount);
    }

    @Override
    @Transactional
    public CloudSyncResultResponse sync(UUID id, CloudSyncRequest request) {
        requireEntity(id);
        List<CloudDeviceItem> items = request != null && request.items() != null ? request.items() : List.of();
        String targetArea = clean(request != null ? request.targetArea() : null);
        boolean overwrite = request != null && Boolean.TRUE.equals(request.overwrite());
        Map<String, CameraResponse> localByIp = cameraService.list().stream()
                .filter(camera -> camera.ip() != null && !camera.ip().isBlank())
                .collect(Collectors.toMap(CameraResponse::ip, Function.identity(), (a, b) -> a, LinkedHashMap::new));
        int created = 0;
        int updated = 0;
        int skipped = 0;
        for (CloudDeviceItem item : items) {
            String ip = clean(item.ip());
            if (ip == null) {
                skipped++;
                continue;
            }
            CameraResponse local = localByIp.get(ip);
            String area = targetArea != null ? targetArea : clean(item.area());
            if (local == null) {
                String sourceUrl = clean(item.sourceUrl());
                if (sourceUrl == null) {
                    skipped++;
                    continue;
                }
                cameraService.create(new CameraCreateRequest(
                        clean(item.name()) != null ? item.name().trim() : ip,
                        sourceUrl,
                        null,
                        area,
                        null, null, null, null,
                        clean(item.protocol()),
                        null,
                        ip,
                        clean(item.port()),
                        null, null, null, null,
                        null, null, null, null, null, null
                ));
                created++;
            } else if (overwrite) {
                cameraService.update(local.id(), new CameraUpdateRequest(
                        clean(item.name()),
                        clean(item.sourceUrl()),
                        null,
                        area,
                        null, null, null, null,
                        clean(item.protocol()),
                        null,
                        ip,
                        clean(item.port()),
                        null, null, null, null,
                        null, null, null, null, null, null
                ));
                updated++;
            } else {
                skipped++;
            }
        }
        return new CloudSyncResultResponse(created, updated, skipped);
    }

    /**
     * 按 IP 判重：云端有本地无 → "new"；同 IP 本地已存在 → "update"（本地无 IP 的摄像头不参与判重）。
     * public 静态以便测试直接覆盖判重逻辑。
     */
    public static List<CloudDeviceItem> diffByIp(List<CloudDeviceItem> cloudDevices, List<CameraResponse> localCameras) {
        Map<String, CameraResponse> localByIp = localCameras.stream()
                .filter(camera -> camera.ip() != null && !camera.ip().isBlank())
                .collect(Collectors.toMap(CameraResponse::ip, Function.identity(), (a, b) -> a));
        List<CloudDeviceItem> items = new ArrayList<>();
        for (CloudDeviceItem device : cloudDevices) {
            String ip = clean(device.ip());
            CameraResponse local = ip != null ? localByIp.get(ip) : null;
            items.add(new CloudDeviceItem(
                    device.name(),
                    device.area(),
                    device.protocol(),
                    device.ip(),
                    device.port(),
                    device.sourceUrl(),
                    local == null ? "new" : "update",
                    local == null ? null : local.id()
            ));
        }
        return items;
    }

    /**
     * 按约定拉取云端设备清单：GET http://{ip}:{port}/api/devices，
     * 请求头携带 X-Access-Key / X-Access-Secret，响应为 JSON 数组，
     * 元素字段：name/area/protocol/ip/port/sourceUrl。
     */
    private List<CloudDeviceItem> fetchCloudDevices(CloudPlatformEntity platform) {
        String ip = clean(platform.getIp());
        String port = clean(platform.getPort());
        if (ip == null || port == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "云平台 IP 或端口未配置");
        }
        HttpRequest httpRequest = HttpRequest.newBuilder()
                .uri(URI.create("http://" + ip + ":" + port + "/api/devices"))
                .timeout(Duration.ofSeconds(15))
                .header("X-Access-Key", platform.getKey() != null ? platform.getKey() : "")
                .header("X-Access-Secret", platform.getSecret() != null ? platform.getSecret() : "")
                .GET()
                .build();
        HttpResponse<String> response;
        try {
            response = httpClient.send(httpRequest, HttpResponse.BodyHandlers.ofString());
        } catch (IOException e) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "云平台不可达: " + e.getMessage(), e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "云平台请求被中断", e);
        }
        if (response.statusCode() < 200 || response.statusCode() >= 300) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "云平台返回 " + response.statusCode());
        }
        try {
            JsonNode root = objectMapper.readTree(response.body());
            JsonNode array = root.isArray() ? root : root.path("data");
            if (!array.isArray()) {
                throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "云平台返回格式不是设备数组");
            }
            List<CloudDeviceItem> devices = new ArrayList<>();
            for (JsonNode node : array) {
                devices.add(new CloudDeviceItem(
                        text(node, "name"),
                        text(node, "area"),
                        text(node, "protocol"),
                        text(node, "ip"),
                        text(node, "port"),
                        text(node, "sourceUrl"),
                        null,
                        null
                ));
            }
            return devices;
        } catch (IOException e) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "云平台响应解析失败: " + e.getMessage(), e);
        }
    }

    private CloudPlatformEntity requireEntity(UUID id) {
        CloudPlatformEntity entity = cloudPlatformDao.selectById(id);
        if (entity == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Cloud platform not found");
        }
        return entity;
    }

    private static String text(JsonNode node, String field) {
        JsonNode value = node.get(field);
        return value != null && value.isTextual() ? value.asText() : null;
    }

    private static String clean(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }

    private CloudPlatformResponse toResponse(CloudPlatformEntity entity) {
        return new CloudPlatformResponse(
                entity.getId(),
                entity.getName(),
                entity.getType(),
                entity.getKey(),
                entity.getSecret(),
                entity.getIp(),
                entity.getPort(),
                entity.getCreatedAt(),
                entity.getUpdatedAt()
        );
    }
}
