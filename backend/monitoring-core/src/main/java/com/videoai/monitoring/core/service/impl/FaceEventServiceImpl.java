package com.videoai.monitoring.core.service.impl;

import com.videoai.monitoring.common.dto.FaceEventCreateRequest;
import com.videoai.monitoring.common.vo.FaceEventResponse;
import com.videoai.monitoring.core.config.VideoAiProperties;
import com.videoai.monitoring.core.dao.FaceEventDao;
import com.videoai.monitoring.core.entity.FaceEventEntity;
import com.videoai.monitoring.core.service.EventStreamService;
import com.videoai.monitoring.core.service.FaceEventService;
import com.videoai.monitoring.core.service.FileStorageService;
import com.videoai.monitoring.core.support.UrlService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

@Service
public class FaceEventServiceImpl implements FaceEventService {
    private final FaceEventDao faceEventDao;
    private final VideoAiProperties properties;
    private final UrlService urlService;
    private final EventStreamService eventStreamService;
    private final FileStorageService fileStorageService;

    public FaceEventServiceImpl(
            FaceEventDao faceEventDao,
            VideoAiProperties properties,
            UrlService urlService,
            EventStreamService eventStreamService,
            FileStorageService fileStorageService
    ) {
        this.faceEventDao = faceEventDao;
        this.properties = properties;
        this.urlService = urlService;
        this.eventStreamService = eventStreamService;
        this.fileStorageService = fileStorageService;
    }

    @Override
    public List<FaceEventResponse> list(UUID cameraId, UUID profileId, int limit) {
        int safeLimit = Math.max(1, Math.min(limit, 200));
        return faceEventDao.selectFiltered(cameraId, profileId, safeLimit)
                .stream()
                .map(this::toResponse)
                .toList();
    }

    @Override
    @Transactional
    public FaceEventResponse create(FaceEventCreateRequest request, String snapshotBase64) {
        if (recentDuplicate(request.cameraId(), request.faceProfileId())) {
            return null;
        }
        String snapshotPath = request.snapshotPath();
        if ((snapshotPath == null || snapshotPath.isBlank()) && snapshotBase64 != null && !snapshotBase64.isBlank()) {
            snapshotPath = fileStorageService.saveSnapshotBase64(snapshotBase64);
        }
        UUID id = UUID.randomUUID();
        FaceEventEntity entity = new FaceEventEntity();
        entity.setId(id);
        entity.setCameraId(request.cameraId());
        entity.setFaceProfileId(request.faceProfileId());
        entity.setCameraName(request.cameraName());
        entity.setProfileName(request.profileName());
        entity.setProfileDescription(request.profileDescription());
        entity.setFacePhotoPath(request.facePhotoPath());
        entity.setSnapshotPath(snapshotPath);
        entity.setVideoTime(request.videoTime());
        entity.setSimilarity(request.similarity());
        faceEventDao.insert(entity);
        FaceEventResponse event = get(id);
        eventStreamService.publish(event);
        return event;
    }

    @Override
    public FaceEventResponse get(UUID id) {
        return toResponse(faceEventDao.selectById(id));
    }

    private boolean recentDuplicate(UUID cameraId, UUID profileId) {
        int count = faceEventDao.countRecent(cameraId, profileId, properties.matching().cooldownSeconds());
        return count > 0;
    }

    private FaceEventResponse toResponse(FaceEventEntity entity) {
        return new FaceEventResponse(
                entity.getId(),
                entity.getCameraId(),
                entity.getFaceProfileId(),
                entity.getCameraName(),
                entity.getProfileName(),
                entity.getProfileDescription(),
                urlService.fileUrl(entity.getFacePhotoPath()),
                urlService.fileUrl(entity.getSnapshotPath()),
                entity.getVideoTime(),
                entity.getSimilarity(),
                entity.getCreatedAt()
        );
    }
}
