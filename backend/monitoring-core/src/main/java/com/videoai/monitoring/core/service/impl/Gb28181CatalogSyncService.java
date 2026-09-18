package com.videoai.monitoring.core.service.impl;

import com.videoai.monitoring.common.dto.CameraCreateRequest;
import com.videoai.monitoring.common.dto.CameraUpdateRequest;
import com.videoai.monitoring.common.dto.CloudDeviceItem;
import com.videoai.monitoring.common.dto.CloudSyncRequest;
import com.videoai.monitoring.common.dto.Gb28181Config;
import com.videoai.monitoring.common.vo.AccessConfigResponse;
import com.videoai.monitoring.common.vo.CameraResponse;
import com.videoai.monitoring.common.vo.CloudSyncPrecheckResponse;
import com.videoai.monitoring.common.vo.CloudSyncResultResponse;
import com.videoai.monitoring.core.dao.Gb28181AccessConfigDao;
import com.videoai.monitoring.core.entity.Gb28181AccessConfigEntity;
import com.videoai.monitoring.core.service.AccessConfigService;
import com.videoai.monitoring.core.service.CameraService;
import com.videoai.monitoring.core.support.Gb28181CatalogClient;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * GB28181 级联服务器设备目录同步：通过 SIP MESSAGE Catalog 查询拉取设备清单，
 * 按 gb_code（国标 DeviceID）判重入库。GB28181 设备无拉流地址，sourceUrl 入库为 null。
 */
@Service
public class Gb28181CatalogSyncService {

    private final Gb28181AccessConfigDao gb28181AccessConfigDao;
    private final AccessConfigService accessConfigService;
    private final CameraService cameraService;
    private final Gb28181CatalogClient catalogClient;

    public Gb28181CatalogSyncService(Gb28181AccessConfigDao gb28181AccessConfigDao,
                                     AccessConfigService accessConfigService,
                                     CameraService cameraService,
                                     Gb28181CatalogClient catalogClient) {
        this.gb28181AccessConfigDao = gb28181AccessConfigDao;
        this.accessConfigService = accessConfigService;
        this.cameraService = cameraService;
        this.catalogClient = catalogClient;
    }

    public CloudSyncPrecheckResponse precheck(UUID entryId) {
        Gb28181AccessConfigEntity entry = requireEntry(entryId);
        List<Gb28181CatalogClient.Gb28181CatalogDevice> catalog = queryCatalog(entry);
        List<CloudDeviceItem> cloudDevices = catalog.stream()
                .map(device -> new CloudDeviceItem(
                        isBlank(device.name()) ? device.deviceId() : device.name().trim(),
                        null,
                        "GB28181",
                        null,
                        null,
                        null,
                        null,
                        null,
                        device.deviceId()))
                .toList();
        List<CloudDeviceItem> items = diffByGbCode(cloudDevices, cameraService.list());
        int newCount = (int) items.stream().filter(item -> "new".equals(item.status())).count();
        int updateCount = (int) items.stream().filter(item -> "update".equals(item.status())).count();
        return new CloudSyncPrecheckResponse(items, newCount, updateCount);
    }

    @Transactional
    public CloudSyncResultResponse sync(UUID entryId, CloudSyncRequest request) {
        requireEntry(entryId);
        List<CloudDeviceItem> items = request != null && request.items() != null ? request.items() : List.of();
        String targetArea = clean(request != null ? request.targetArea() : null);
        boolean overwrite = request != null && Boolean.TRUE.equals(request.overwrite());
        Map<String, CameraResponse> localByGbCode = cameraService.list().stream()
                .filter(camera -> !isBlank(camera.gbCode()))
                .collect(Collectors.toMap(CameraResponse::gbCode, Function.identity(), (a, b) -> a,
                        LinkedHashMap::new));
        int created = 0;
        int updated = 0;
        int skipped = 0;
        for (CloudDeviceItem item : items) {
            String gbCode = clean(item.gbCode());
            if (gbCode == null) {
                skipped++;
                continue;
            }
            CameraResponse local = localByGbCode.get(gbCode);
            String area = targetArea != null ? targetArea : clean(item.area());
            if (local == null) {
                cameraService.create(new CameraCreateRequest(
                        clean(item.name()) != null ? item.name().trim() : gbCode,
                        null,
                        null,
                        area,
                        null, null, null, null,
                        "GB28181",
                        null,
                        null,
                        null,
                        null, null, null, null,
                        null, null, null, null, null, null,
                        null,
                        null, null, null, null, null,
                        gbCode,
                        null
                ));
                created++;
            } else if (overwrite) {
                // 只覆盖 name/area/gbCode；sourceUrl 传 null 保留旧值
                cameraService.update(local.id(), new CameraUpdateRequest(
                        clean(item.name()),
                        null,
                        null,
                        area,
                        null, null, null, null,
                        null,
                        null,
                        null,
                        null,
                        null, null, null, null,
                        null, null, null, null, null, null,
                        null,
                        null, null, null, null, null,
                        gbCode,
                        null
                ));
                updated++;
            } else {
                skipped++;
            }
        }
        return new CloudSyncResultResponse(created, updated, skipped);
    }

    /**
     * 按 gbCode 判重：云端有本地无 → "new"；同 gbCode 本地已存在 → "update"
     * （本地无 gbCode 的摄像头不参与判重；云端无 deviceId 的条目跳过）。
     * public 静态以便测试直接覆盖判重逻辑。
     */
    public static List<CloudDeviceItem> diffByGbCode(List<CloudDeviceItem> cloudDevices,
                                                     List<CameraResponse> localCameras) {
        Map<String, CameraResponse> localByGbCode = localCameras.stream()
                .filter(camera -> camera.gbCode() != null && !camera.gbCode().isBlank())
                .collect(Collectors.toMap(CameraResponse::gbCode, Function.identity(), (a, b) -> a));
        List<CloudDeviceItem> items = new ArrayList<>();
        for (CloudDeviceItem device : cloudDevices) {
            String gbCode = clean(device.gbCode());
            if (gbCode == null) {
                continue;
            }
            CameraResponse local = localByGbCode.get(gbCode);
            items.add(new CloudDeviceItem(
                    device.name(),
                    device.area(),
                    device.protocol(),
                    device.ip(),
                    device.port(),
                    device.sourceUrl(),
                    local == null ? "new" : "update",
                    local == null ? null : local.id(),
                    device.gbCode()
            ));
        }
        return items;
    }

    private List<Gb28181CatalogClient.Gb28181CatalogDevice> queryCatalog(Gb28181AccessConfigEntity entry) {
        if (isBlank(entry.getSipId())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请先在接入配置页配置级联服务器SIP ID");
        }
        AccessConfigResponse accessConfig = accessConfigService.get();
        Gb28181Config local = accessConfig != null ? accessConfig.gb28181() : null;
        if (local == null || isBlank(local.sipId()) || isBlank(local.sipDomain())
                || isBlank(local.sipIp()) || isBlank(local.sipPort())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST,
                    "请先在接入配置页配置本级GB28181 SIP参数（sipId/sipDomain/sipIp/sipPort）");
        }
        Gb28181CatalogClient.TargetServer target = new Gb28181CatalogClient.TargetServer(
                entry.getSipId().trim(),
                entry.getSipIp() != null ? entry.getSipIp().trim() : null,
                entry.getSipPort() != null ? entry.getSipPort().trim() : null,
                entry.getUsername(),
                entry.getPassword());
        try {
            return catalogClient.queryCatalog(
                    new Gb28181CatalogClient.LocalSipConfig(local.sipId(), local.sipDomain(),
                            local.sipIp(), local.sipPort()),
                    target);
        } catch (Gb28181CatalogClient.CatalogQueryException exception) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, exception.getMessage(), exception);
        }
    }

    private Gb28181AccessConfigEntity requireEntry(UUID entryId) {
        Gb28181AccessConfigEntity entry = gb28181AccessConfigDao.selectById(entryId);
        if (entry == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "GB28181 级联服务器条目不存在");
        }
        return entry;
    }

    private static boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    private static String clean(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }
}
