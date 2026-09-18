package com.videoai.monitoring.core.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.videoai.monitoring.common.dto.CameraCreateRequest;
import com.videoai.monitoring.common.dto.CameraUpdateRequest;
import com.videoai.monitoring.common.vo.CameraResponse;
import com.videoai.monitoring.common.vo.DeviceEventMessage;
import com.videoai.monitoring.core.client.DeviceSourceProbe;
import com.videoai.monitoring.core.client.ZlmClient;
import com.videoai.monitoring.core.config.VideoAiProperties;
import com.videoai.monitoring.core.dao.CameraDao;
import com.videoai.monitoring.core.entity.CameraEntity;
import com.videoai.monitoring.core.service.CameraService;
import com.videoai.monitoring.core.service.LiveRelayService;
import com.videoai.monitoring.core.service.OpenSubscriptionService;
import com.videoai.monitoring.core.service.preview.PreviewRelayManager;
import com.videoai.monitoring.core.support.AreaPaths;
import com.videoai.monitoring.core.support.OpenDevicePayloads;
import com.videoai.monitoring.core.support.StreamUrls;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.net.URI;
import java.time.OffsetDateTime;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.stream.Collectors;

@Service
public class CameraServiceImpl implements CameraService {
    private static final Logger log = LoggerFactory.getLogger(CameraServiceImpl.class);

    private final CameraDao cameraDao;
    private final VideoAiProperties properties;
    private final ZlmClient zlmClient;
    private final LiveRelayService liveRelayService;
    private final PreviewRelayManager previewRelayManager;
    private final OpenSubscriptionService openSubscriptionService;
    private final DeviceSourceProbe serialNumberResolver = new DeviceSourceProbe();
    /** 序列号回取走后台线程：慢速设备不能阻塞创建接口 */
    private final ExecutorService serialFetchExecutor = Executors.newSingleThreadExecutor(runnable -> {
        Thread thread = new Thread(runnable, "camera-serial-fetch");
        thread.setDaemon(true);
        return thread;
    });

    public CameraServiceImpl(CameraDao cameraDao, VideoAiProperties properties, ZlmClient zlmClient,
                             LiveRelayService liveRelayService, PreviewRelayManager previewRelayManager,
                             OpenSubscriptionService openSubscriptionService) {
        this.cameraDao = cameraDao;
        this.properties = properties;
        this.zlmClient = zlmClient;
        this.liveRelayService = liveRelayService;
        this.previewRelayManager = previewRelayManager;
        this.openSubscriptionService = openSubscriptionService;
    }

    @Override
    public List<CameraResponse> list() {
        return cameraDao.selectAllOrdered().stream().map(this::toResponse).toList();
    }

    @Override
    public CameraResponse get(UUID id) {
        return find(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Camera not found"));
    }

    @Override
    public Optional<CameraResponse> find(UUID id) {
        return Optional.ofNullable(cameraDao.selectById(id)).map(this::toResponse);
    }

    @Override
    public List<CameraResponse> findByStreamName(String streamName) {
        return cameraDao.selectByStreamName(streamName).stream().map(this::toResponse).toList();
    }

    @Override
    @Transactional
    public CameraResponse create(CameraCreateRequest request) {
        UUID id = UUID.randomUUID();
        String streamName = StreamUrls.streamNameFromSource(request.sourceUrl());
        if (streamName == null || streamName.isEmpty()) {
            streamName = id.toString();
        }
        String area = AreaPaths.normalize(request.area());
        CameraEntity entity = new CameraEntity();
        entity.setId(id);
        entity.setName(request.name());
        entity.setSourceUrl(request.sourceUrl());
        entity.setStreamApp("live");
        entity.setStreamName(streamName);
        // 新建设备默认未开播：cameras.status 为非空列
        entity.setStatus("STOPPED");
        // created_at/updated_at 非空；MP 默认策略会跳过 null 字段，必须显式赋值
        OffsetDateTime now = OffsetDateTime.now();
        entity.setCreatedAt(now);
        entity.setUpdatedAt(now);
        entity.setDescription(request.description());
        entity.setArea(area != null ? area : "办公楼");
        entity.setNvrId(clean(request.nvrId()));
        entity.setNvrChannel(clean(request.nvrChannel()));
        entity.setNvrTrackId(clean(request.nvrTrackId()));
        entity.setNvrStreamType(clean(request.nvrStreamType()));
        entity.setProtocol(clean(request.protocol()));
        entity.setVendor(clean(request.vendor()));
        entity.setIp(clean(request.ip()));
        entity.setPort(clean(request.port()));
        entity.setUsername(clean(request.username()));
        entity.setPassword(clean(request.password()));
        String deviceCode = clean(request.deviceCode());
        // 未填设备编号时按 CAM%05d 自动分配（新增页已不再手填该字段）
        entity.setDeviceCode(deviceCode != null ? deviceCode : nextDeviceCode());
        entity.setSerialNumber(clean(request.serialNumber()));
        entity.setVideoPreviewEnabled(request.videoPreviewEnabled() != null ? request.videoPreviewEnabled() : Boolean.TRUE);
        entity.setAudioEnabled(request.audioEnabled() != null ? request.audioEnabled() : Boolean.FALSE);
        entity.setTalkbackEnabled(request.talkbackEnabled() != null ? request.talkbackEnabled() : Boolean.FALSE);
        entity.setPtzEnabled(request.ptzEnabled() != null ? request.ptzEnabled() : Boolean.FALSE);
        entity.setSmartAnalysisEnabled(request.smartAnalysisEnabled() != null ? request.smartAnalysisEnabled() : Boolean.FALSE);
        entity.setAlarmIoEnabled(request.alarmIoEnabled() != null ? request.alarmIoEnabled() : Boolean.FALSE);
        entity.setCloudPlatformId(request.cloudPlatformId());
        entity.setDeviceCategory(clean(request.deviceCategory()));
        entity.setDeviceType(clean(request.deviceType()));
        entity.setProtocolVersion(clean(request.protocolVersion()));
        entity.setRegisterExpire(request.registerExpire());
        entity.setHeartbeat(request.heartbeat());
        entity.setGbCode(clean(request.gbCode()));
        entity.setChannelName(clean(request.channelName()));
        cameraDao.insert(entity);
        scheduleSerialNumberFetch(id, request.sourceUrl());
        CameraResponse created = get(id);
        openSubscriptionService.publishCamera(DeviceEventMessage.CREATED, created);
        return created;
    }

    /** 下一个自动设备编号：CAM00001 起，按库内已有 CAM%05d 最大值递增。 */
    private String nextDeviceCode() {
        int max = 0;
        List<String> codes = cameraDao.selectCamDeviceCodes();
        if (codes == null) {
            return String.format("CAM%05d", 1);
        }
        for (String code : codes) {
            if (code == null || code.length() != 8) {
                continue;
            }
            try {
                max = Math.max(max, Integer.parseInt(code.substring(3)));
            } catch (NumberFormatException ignored) {
                // 非纯数字尾缀不参与编号分配
            }
        }
        return String.format("CAM%05d", max + 1);
    }

    /** 创建后异步回取设备序列号；回取失败或设备不支持时留空，不影响创建结果。 */
    private void scheduleSerialNumberFetch(UUID id, String sourceUrl) {
        if (!DeviceSourceProbe.isResolvable(sourceUrl)) {
            return;
        }
        serialFetchExecutor.submit(() -> {
            try {
                Optional<String> serial = serialNumberResolver.resolveSerialNumber(sourceUrl);
                if (serial.isEmpty()) {
                    return;
                }
                CameraEntity fresh = cameraDao.selectById(id);
                if (fresh == null) {
                    return;
                }
                // 用户已在编辑页手填序列号时不覆盖
                if (fresh.getSerialNumber() != null && !fresh.getSerialNumber().isBlank()) {
                    return;
                }
                fresh.setSerialNumber(serial.get());
                cameraDao.updateCamera(fresh);
                openSubscriptionService.publishCamera(DeviceEventMessage.UPDATED, toResponse(fresh));
            } catch (Exception ignored) {
                // 序列号回取失败不影响设备创建
            }
        });
    }

    @Override
    @Transactional
    public CameraResponse update(UUID id, CameraUpdateRequest request) {
        CameraResponse old = get(id);
        String newName = request.name() != null ? request.name() : old.name();
        String newSourceUrl = request.sourceUrl() != null ? request.sourceUrl() : old.sourceUrl();
        String newDescription = request.description() != null ? request.description() : old.description();
        String newArea = request.area() != null ? AreaPaths.normalize(request.area()) : old.area();
        String streamName = StreamUrls.streamNameFromSource(newSourceUrl);
        if (streamName == null || streamName.isEmpty()) {
            streamName = old.streamName();
        }
        CameraEntity entity = new CameraEntity();
        entity.setId(id);
        entity.setName(newName);
        entity.setSourceUrl(newSourceUrl);
        entity.setDescription(newDescription);
        entity.setArea(newArea);
        entity.setStreamName(streamName);
        entity.setNvrId(request.nvrId() != null ? clean(request.nvrId()) : old.nvrId());
        entity.setNvrChannel(request.nvrChannel() != null ? clean(request.nvrChannel()) : old.nvrChannel());
        entity.setNvrTrackId(request.nvrTrackId() != null ? clean(request.nvrTrackId()) : old.nvrTrackId());
        entity.setNvrStreamType(request.nvrStreamType() != null ? clean(request.nvrStreamType()) : old.nvrStreamType());
        entity.setProtocol(request.protocol() != null ? clean(request.protocol()) : old.protocol());
        entity.setVendor(request.vendor() != null ? clean(request.vendor()) : old.vendor());
        entity.setIp(request.ip() != null ? clean(request.ip()) : old.ip());
        entity.setPort(request.port() != null ? clean(request.port()) : old.port());
        entity.setUsername(request.username() != null ? clean(request.username()) : old.username());
        entity.setPassword(request.password() != null ? clean(request.password()) : old.password());
        // 设备编号留空（含历史数据为空串）时按 CAM%05d 自动分配
        String deviceCode = clean(request.deviceCode() != null ? request.deviceCode() : old.deviceCode());
        entity.setDeviceCode(deviceCode != null ? deviceCode : nextDeviceCode());
        String serialNumber = clean(request.serialNumber() != null ? request.serialNumber() : old.serialNumber());
        entity.setSerialNumber(serialNumber);
        entity.setVideoPreviewEnabled(request.videoPreviewEnabled() != null ? request.videoPreviewEnabled() : old.videoPreviewEnabled());
        entity.setAudioEnabled(request.audioEnabled() != null ? request.audioEnabled() : old.audioEnabled());
        entity.setTalkbackEnabled(request.talkbackEnabled() != null ? request.talkbackEnabled() : old.talkbackEnabled());
        entity.setPtzEnabled(request.ptzEnabled() != null ? request.ptzEnabled() : old.ptzEnabled());
        entity.setSmartAnalysisEnabled(request.smartAnalysisEnabled() != null ? request.smartAnalysisEnabled() : old.smartAnalysisEnabled());
        entity.setAlarmIoEnabled(request.alarmIoEnabled() != null ? request.alarmIoEnabled() : old.alarmIoEnabled());
        entity.setCloudPlatformId(request.cloudPlatformId() != null ? request.cloudPlatformId() : old.cloudPlatformId());
        entity.setDeviceCategory(request.deviceCategory() != null ? clean(request.deviceCategory()) : old.deviceCategory());
        entity.setDeviceType(request.deviceType() != null ? clean(request.deviceType()) : old.deviceType());
        entity.setProtocolVersion(request.protocolVersion() != null ? clean(request.protocolVersion()) : old.protocolVersion());
        entity.setRegisterExpire(request.registerExpire() != null ? request.registerExpire() : old.registerExpire());
        entity.setHeartbeat(request.heartbeat() != null ? request.heartbeat() : old.heartbeat());
        entity.setGbCode(request.gbCode() != null ? clean(request.gbCode()) : old.gbCode());
        entity.setChannelName(request.channelName() != null ? clean(request.channelName()) : old.channelName());
        cameraDao.updateCamera(entity);
        // 序列号为空时后台回取（编辑页改了拉流地址直接保存也覆盖到）
        if (serialNumber == null) {
            scheduleSerialNumberFetch(id, newSourceUrl);
        }
        if (!Objects.equals(newSourceUrl, old.sourceUrl()) || !Objects.equals(streamName, old.streamName())) {
            previewRelayManager.stopStream(old.streamName());
            liveRelayService.stopFfmpegLiveRelay(old.streamName());
            liveRelayService.removeZlmediakitProxy(StreamUrls.subStreamName(old.streamName()));
        }
        // 音频能力开关切换：关闭主流代理，由守护线程按新模式（ffmpeg 转 AAC / ZLM 透传）重挂
        if (!Objects.equals(entity.getAudioEnabled(), old.audioEnabled()) && "RUNNING".equals(old.status())) {
            liveRelayService.removeZlmediakitProxy(streamName);
        }
        CameraResponse updated = get(id);
        openSubscriptionService.publishCamera(DeviceEventMessage.UPDATED, updated);
        return updated;
    }

    @Override
    @Transactional
    public void delete(UUID id) {
        find(id).ifPresent(camera -> {
            previewRelayManager.stopStream(camera.streamName());
            liveRelayService.removeZlmediakitProxy(camera.streamName());
            liveRelayService.removeZlmediakitProxy(StreamUrls.subStreamName(camera.streamName()));
            cameraDao.deleteById(id);
            openSubscriptionService.publish(DeviceEventMessage.DELETED,
                    OpenDevicePayloads.deletedDevice(camera.id(), camera.name()));
        });
    }

    @Override
    @Transactional
    public CameraResponse start(UUID id) {
        CameraResponse camera = get(id);
        // 无拉流地址的设备（如 GB28181 同步入库）无法开播
        if (camera.sourceUrl() == null || camera.sourceUrl().isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "该设备未配置拉流地址，无法开播");
        }
        // 先挂流再置状态：拉流服务拒绝该地址时不得留下"拉流中"的假状态
        // 支持音频的设备走 ffmpeg 中继转 AAC（浏览器 MSE 不支持摄像头常见的 G.711）
        boolean attached = liveRelayService.addZlmediakitProxy(
                camera.sourceUrl(), camera.streamName(), false, camera.audioEnabled());
        if (!attached) {
            cameraDao.updateStatus(id, "STOPPED");
            log.warn("camera start rejected by relay: {} ({}) url={}", camera.name(), id, camera.sourceUrl());
            throw new ResponseStatusException(HttpStatus.CONFLICT,
                    "设备拉流失败：拉流服务拒绝了该地址，请检查拉流地址、通道号与凭据");
        }
        cameraDao.updateStatus(id, "RUNNING");
        // 可推导子码流地址的设备同时注册子码流代理（{streamName}-sub），供预览页切换
        String subSourceUrl = StreamUrls.deriveSubSourceUrl(camera.sourceUrl());
        if (subSourceUrl != null) {
            liveRelayService.addZlmediakitProxy(subSourceUrl, StreamUrls.subStreamName(camera.streamName()));
        }
        return get(id);
    }

    @Override
    @Transactional
    public CameraResponse stop(UUID id) {
        CameraResponse camera = get(id);
        previewRelayManager.stopStream(camera.streamName());
        liveRelayService.removeZlmediakitProxy(camera.streamName());
        liveRelayService.removeZlmediakitProxy(StreamUrls.subStreamName(camera.streamName()));
        cameraDao.updateStatus(id, "STOPPED");
        return get(id);
    }

    @Override
    public Map<String, Object> mediaList() {
        return zlmClient.mediaList();
    }

    @Override
    public long countByCloudPlatformId(UUID cloudPlatformId) {
        return cameraDao.selectCount(
                new LambdaQueryWrapper<CameraEntity>().eq(CameraEntity::getCloudPlatformId, cloudPlatformId));
    }

    /** camera_with_runtime_flags: objectDetectionEnabled is derived from the source host. */
    @Override
    public boolean isDinoCamera(String sourceUrl) {
        if (sourceUrl == null) {
            return false;
        }
        String host = StreamUrls.hostOf(sourceUrl);
        return host != null && dinoCameraHosts().contains(host);
    }

    private Set<String> dinoCameraHosts() {
        String configured = properties.dinoCameraHosts();
        if (configured == null || configured.isBlank()) {
            return Set.of();
        }
        return Arrays.stream(configured.split(","))
                .map(String::trim)
                .filter(item -> !item.isEmpty())
                .collect(Collectors.toSet());
    }

    private CameraResponse toResponse(CameraEntity entity) {
        String sourceUrl = entity.getSourceUrl();
        String stream = entity.getStreamName();
        String playbackUrl = StreamUrls.playbackUrl(properties.zlm().publicHttpUrl(), sourceUrl, stream);
        return new CameraResponse(
                entity.getId(),
                entity.getName(),
                sourceUrl,
                entity.getStreamApp(),
                stream,
                entity.getFfmpegKey(),
                entity.getDescription(),
                entity.getArea(),
                entity.getStatus(),
                entity.getOnlineStatus() != null ? entity.getOnlineStatus() : "UNKNOWN",
                playbackUrl,
                entity.getCreatedAt(),
                entity.getUpdatedAt(),
                entity.getNvrId(),
                entity.getNvrChannel(),
                entity.getNvrTrackId(),
                entity.getNvrStreamType(),
                // 历史设备仅落库了拉流地址：协议/IP/端口/凭据缺失时从 sourceUrl 推导，供详情页展示
                entity.getProtocol() != null ? entity.getProtocol() : protocolFrom(sourceUrl),
                entity.getVendor(),
                entity.getIp() != null ? entity.getIp() : StreamUrls.hostOf(sourceUrl),
                entity.getPort() != null ? entity.getPort() : portFrom(sourceUrl),
                entity.getUsername() != null ? entity.getUsername() : credentialFrom(sourceUrl, true),
                entity.getPassword() != null ? entity.getPassword() : credentialFrom(sourceUrl, false),
                entity.getDeviceCode(),
                entity.getSerialNumber(),
                isDinoCamera(sourceUrl),
                Boolean.TRUE.equals(entity.getVideoPreviewEnabled()),
                Boolean.TRUE.equals(entity.getAudioEnabled()),
                Boolean.TRUE.equals(entity.getTalkbackEnabled()),
                Boolean.TRUE.equals(entity.getPtzEnabled()),
                Boolean.TRUE.equals(entity.getSmartAnalysisEnabled()),
                Boolean.TRUE.equals(entity.getAlarmIoEnabled()),
                // 子码流流名由 sourceUrl 按厂商约定推导；无法推导的设备为 null（前端禁用切换）
                StreamUrls.deriveSubSourceUrl(sourceUrl) != null ? StreamUrls.subStreamName(stream) : null,
                entity.getCloudPlatformId(),
                entity.getDeviceCategory(),
                entity.getDeviceType(),
                entity.getProtocolVersion(),
                entity.getRegisterExpire(),
                entity.getHeartbeat(),
                entity.getGbCode(),
                entity.getChannelName()
        );
    }

    private String clean(String value) {
        if (value == null) {
            return null;
        }
        String cleaned = value.trim();
        return cleaned.isEmpty() ? null : cleaned;
    }

    // --- 从拉流地址推导设备接入信息（老数据未落库 protocol/ip/port/username/password 时兜底） ---

    private static String protocolFrom(String sourceUrl) {
        if (sourceUrl == null) {
            return null;
        }
        String lower = sourceUrl.toLowerCase();
        if (lower.startsWith("rtsp://")) {
            return "RTSP 拉流";
        }
        if (lower.startsWith("rtmp://")) {
            return "RTMP 推流";
        }
        if (lower.startsWith("http://") || lower.startsWith("https://")) {
            return "HTTP 拉流";
        }
        return null;
    }

    private static String portFrom(String sourceUrl) {
        if (sourceUrl == null) {
            return null;
        }
        try {
            int port = URI.create(sourceUrl).getPort();
            return port >= 0 ? String.valueOf(port) : null;
        } catch (IllegalArgumentException exception) {
            return null;
        }
    }

    private static String credentialFrom(String sourceUrl, boolean username) {
        if (sourceUrl == null) {
            return null;
        }
        try {
            String userInfo = URI.create(sourceUrl).getUserInfo();
            if (userInfo == null || userInfo.isEmpty()) {
                return null;
            }
            int colon = userInfo.indexOf(':');
            if (username) {
                return colon >= 0 ? userInfo.substring(0, colon) : userInfo;
            }
            return colon >= 0 ? userInfo.substring(colon + 1) : null;
        } catch (IllegalArgumentException exception) {
            return null;
        }
    }
}
