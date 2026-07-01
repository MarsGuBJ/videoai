package com.videoai.monitoring.service;

import com.videoai.monitoring.config.VideoAiProperties;
import com.videoai.monitoring.dto.EventDtos.FaceEventCreateRequest;
import com.videoai.monitoring.dto.EventDtos.FaceEventResponse;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

@Service
public class FaceEventService {
    private final JdbcClient jdbcClient;
    private final VideoAiProperties properties;
    private final UrlService urlService;
    private final EventStreamService eventStreamService;
    private final FileStorageService fileStorageService;

    public FaceEventService(
            JdbcClient jdbcClient,
            VideoAiProperties properties,
            UrlService urlService,
            EventStreamService eventStreamService,
            FileStorageService fileStorageService
    ) {
        this.jdbcClient = jdbcClient;
        this.properties = properties;
        this.urlService = urlService;
        this.eventStreamService = eventStreamService;
        this.fileStorageService = fileStorageService;
    }

    public List<FaceEventResponse> list(UUID cameraId, UUID profileId, int limit) {
        int safeLimit = Math.max(1, Math.min(limit, 200));
        StringBuilder sql = new StringBuilder("SELECT * FROM face_events WHERE 1=1");
        if (cameraId != null) {
            sql.append(" AND camera_id = :cameraId");
        }
        if (profileId != null) {
            sql.append(" AND face_profile_id = :profileId");
        }
        sql.append(" ORDER BY created_at DESC LIMIT :limit");

        JdbcClient.StatementSpec spec = jdbcClient.sql(sql.toString()).param("limit", safeLimit);
        if (cameraId != null) {
            spec = spec.param("cameraId", cameraId);
        }
        if (profileId != null) {
            spec = spec.param("profileId", profileId);
        }
        return spec.query(this::map).list();
    }

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
        jdbcClient.sql("""
                        INSERT INTO face_events
                        (id, camera_id, face_profile_id, camera_name, profile_name, profile_description,
                         face_photo_path, snapshot_path, video_time, similarity)
                        VALUES
                        (:id, :cameraId, :faceProfileId, :cameraName, :profileName, :profileDescription,
                         :facePhotoPath, :snapshotPath, :videoTime, :similarity)
                        """)
                .param("id", id)
                .param("cameraId", request.cameraId())
                .param("faceProfileId", request.faceProfileId())
                .param("cameraName", request.cameraName())
                .param("profileName", request.profileName())
                .param("profileDescription", request.profileDescription())
                .param("facePhotoPath", request.facePhotoPath())
                .param("snapshotPath", snapshotPath)
                .param("videoTime", request.videoTime())
                .param("similarity", request.similarity())
                .update();
        FaceEventResponse event = get(id);
        eventStreamService.publish(event);
        return event;
    }

    public FaceEventResponse get(UUID id) {
        return jdbcClient.sql("SELECT * FROM face_events WHERE id = :id")
                .param("id", id)
                .query(this::map)
                .single();
    }

    private boolean recentDuplicate(UUID cameraId, UUID profileId) {
        Integer count = jdbcClient.sql("""
                        SELECT COUNT(*)
                        FROM face_events
                        WHERE camera_id = :cameraId
                          AND face_profile_id = :profileId
                          AND created_at > now() - (:cooldownSeconds || ' seconds')::interval
                        """)
                .param("cameraId", cameraId)
                .param("profileId", profileId)
                .param("cooldownSeconds", properties.matching().cooldownSeconds())
                .query(Integer.class)
                .single();
        return count != null && count > 0;
    }

    private FaceEventResponse map(ResultSet rs, int rowNum) throws SQLException {
        return new FaceEventResponse(
                rs.getObject("id", UUID.class),
                rs.getObject("camera_id", UUID.class),
                rs.getObject("face_profile_id", UUID.class),
                rs.getString("camera_name"),
                rs.getString("profile_name"),
                rs.getString("profile_description"),
                urlService.fileUrl(rs.getString("face_photo_path")),
                urlService.fileUrl(rs.getString("snapshot_path")),
                rs.getObject("video_time", OffsetDateTime.class),
                rs.getDouble("similarity"),
                rs.getObject("created_at", OffsetDateTime.class)
        );
    }
}

