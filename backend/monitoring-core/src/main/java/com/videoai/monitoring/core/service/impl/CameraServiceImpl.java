package com.videoai.monitoring.core.service.impl;

import com.videoai.monitoring.common.dto.CameraCreateRequest;
import com.videoai.monitoring.common.dto.CameraUpdateRequest;
import com.videoai.monitoring.common.vo.CameraResponse;
import com.videoai.monitoring.core.client.ZlmClient;
import com.videoai.monitoring.core.config.VideoAiProperties;
import com.videoai.monitoring.core.dao.CameraDao;
import com.videoai.monitoring.core.entity.CameraEntity;
import com.videoai.monitoring.core.service.CameraService;
import com.videoai.monitoring.core.service.LiveRelayService;
import com.videoai.monitoring.core.service.preview.PreviewRelayManager;
import com.videoai.monitoring.core.support.StreamUrls;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
public class CameraServiceImpl implements CameraService {
    private final CameraDao cameraDao;
    private final VideoAiProperties properties;
    private final ZlmClient zlmClient;
    private final LiveRelayService liveRelayService;
    private final PreviewRelayManager previewRelayManager;

    public CameraServiceImpl(CameraDao cameraDao, VideoAiProperties properties, ZlmClient zlmClient,
                             LiveRelayService liveRelayService, PreviewRelayManager previewRelayManager) {
        this.cameraDao = cameraDao;
        this.properties = properties;
        this.zlmClient = zlmClient;
        this.liveRelayService = liveRelayService;
        this.previewRelayManager = previewRelayManager;
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
        String area = clean(request.area());
        CameraEntity entity = new CameraEntity();
        entity.setId(id);
        entity.setName(request.name());
        entity.setSourceUrl(request.sourceUrl());
        entity.setStreamApp("live");
        entity.setStreamName(streamName);
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
        entity.setDeviceCode(clean(request.deviceCode()));
        entity.setSerialNumber(clean(request.serialNumber()));
        cameraDao.insert(entity);
        return get(id);
    }

    @Override
    @Transactional
    public CameraResponse update(UUID id, CameraUpdateRequest request) {
        CameraResponse old = get(id);
        String newName = request.name() != null ? request.name() : old.name();
        String newSourceUrl = request.sourceUrl() != null ? request.sourceUrl() : old.sourceUrl();
        String newDescription = request.description() != null ? request.description() : old.description();
        String newArea = request.area() != null ? request.area() : old.area();
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
        entity.setDeviceCode(request.deviceCode() != null ? clean(request.deviceCode()) : old.deviceCode());
        entity.setSerialNumber(request.serialNumber() != null ? clean(request.serialNumber()) : old.serialNumber());
        cameraDao.updateCamera(entity);
        if (!newSourceUrl.equals(old.sourceUrl()) || !streamName.equals(old.streamName())) {
            previewRelayManager.stopStream(old.streamName());
            liveRelayService.stopFfmpegLiveRelay(old.streamName());
        }
        return get(id);
    }

    @Override
    @Transactional
    public void delete(UUID id) {
        find(id).ifPresent(camera -> {
            previewRelayManager.stopStream(camera.streamName());
            liveRelayService.removeZlmediakitProxy(camera.streamName());
            cameraDao.deleteById(id);
        });
    }

    @Override
    @Transactional
    public CameraResponse start(UUID id) {
        CameraResponse camera = get(id);
        cameraDao.updateStatus(id, "RUNNING");
        liveRelayService.addZlmediakitProxy(camera.sourceUrl(), camera.streamName());
        return get(id);
    }

    @Override
    @Transactional
    public CameraResponse stop(UUID id) {
        CameraResponse camera = get(id);
        previewRelayManager.stopStream(camera.streamName());
        liveRelayService.removeZlmediakitProxy(camera.streamName());
        cameraDao.updateStatus(id, "STOPPED");
        return get(id);
    }

    @Override
    public Map<String, Object> mediaList() {
        return zlmClient.mediaList();
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
                playbackUrl,
                entity.getCreatedAt(),
                entity.getUpdatedAt(),
                entity.getNvrId(),
                entity.getNvrChannel(),
                entity.getNvrTrackId(),
                entity.getNvrStreamType(),
                entity.getProtocol(),
                entity.getVendor(),
                entity.getIp(),
                entity.getPort(),
                entity.getUsername(),
                entity.getPassword(),
                entity.getDeviceCode(),
                entity.getSerialNumber(),
                isDinoCamera(sourceUrl)
        );
    }

    private String clean(String value) {
        if (value == null) {
            return null;
        }
        String cleaned = value.trim();
        return cleaned.isEmpty() ? null : cleaned;
    }
}
