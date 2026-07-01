package com.videoai.monitoring.service;

import com.videoai.monitoring.client.WorkerClient;
import com.videoai.monitoring.client.ZlmClient;
import com.videoai.monitoring.config.VideoAiProperties;
import com.videoai.monitoring.dto.CameraDtos.CameraCreateRequest;
import com.videoai.monitoring.dto.CameraDtos.CameraResponse;
import com.videoai.monitoring.dto.CameraDtos.CameraUpdateRequest;
import com.videoai.monitoring.dto.WorkerDtos.WorkerStartRequest;
import com.videoai.monitoring.dto.WorkerDtos.WorkerStopRequest;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class CameraService {
    private final JdbcClient jdbcClient;
    private final VideoAiProperties properties;
    private final ZlmClient zlmClient;
    private final WorkerClient workerClient;

    public CameraService(JdbcClient jdbcClient, VideoAiProperties properties, ZlmClient zlmClient, WorkerClient workerClient) {
        this.jdbcClient = jdbcClient;
        this.properties = properties;
        this.zlmClient = zlmClient;
        this.workerClient = workerClient;
    }

    public List<CameraResponse> list() {
        return jdbcClient.sql("SELECT * FROM cameras ORDER BY created_at DESC")
                .query(this::map)
                .list();
    }

    public CameraResponse get(UUID id) {
        return jdbcClient.sql("SELECT * FROM cameras WHERE id = :id")
                .param("id", id)
                .query(this::map)
                .optional()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Camera not found"));
    }

    @Transactional
    public CameraResponse create(CameraCreateRequest request) {
        UUID id = UUID.randomUUID();
        String streamName = id.toString();
        jdbcClient.sql("""
                        INSERT INTO cameras (id, name, source_url, stream_app, stream_name, description,
                                             nvr_id, nvr_channel, nvr_track_id, nvr_stream_type)
                        VALUES (:id, :name, :sourceUrl, 'live', :streamName, :description,
                                :nvrId, :nvrChannel, :nvrTrackId, :nvrStreamType)
                        """)
                .param("id", id)
                .param("name", request.name())
                .param("sourceUrl", request.sourceUrl())
                .param("streamName", streamName)
                .param("description", request.description())
                .param("nvrId", clean(request.nvrId()))
                .param("nvrChannel", clean(request.nvrChannel()))
                .param("nvrTrackId", clean(request.nvrTrackId()))
                .param("nvrStreamType", clean(request.nvrStreamType()))
                .update();
        return get(id);
    }

    @Transactional
    public CameraResponse update(UUID id, CameraUpdateRequest request) {
        jdbcClient.sql("""
                        UPDATE cameras
                        SET name = :name,
                            source_url = :sourceUrl,
                            description = :description,
                            nvr_id = :nvrId,
                            nvr_channel = :nvrChannel,
                            nvr_track_id = :nvrTrackId,
                            nvr_stream_type = :nvrStreamType,
                            updated_at = now()
                        WHERE id = :id
                        """)
                .param("id", id)
                .param("name", request.name())
                .param("sourceUrl", request.sourceUrl())
                .param("description", request.description())
                .param("nvrId", clean(request.nvrId()))
                .param("nvrChannel", clean(request.nvrChannel()))
                .param("nvrTrackId", clean(request.nvrTrackId()))
                .param("nvrStreamType", clean(request.nvrStreamType()))
                .update();
        return get(id);
    }

    @Transactional
    public void delete(UUID id) {
        CameraResponse camera = get(id);
        if ("RUNNING".equals(camera.status())) {
            stop(id);
        }
        jdbcClient.sql("DELETE FROM cameras WHERE id = :id")
                .param("id", id)
                .update();
    }

    @Transactional
    public CameraResponse start(UUID id) {
        CameraResponse camera = get(id);
        if (isPublishedMediaSource(camera.sourceUrl())) {
            jdbcClient.sql("UPDATE cameras SET status = 'RUNNING', ffmpeg_key = NULL, updated_at = now() WHERE id = :id")
                    .param("id", id)
                    .update();
            CameraResponse updated = get(id);
            try {
                workerClient.startStream(new WorkerStartRequest(updated.id(), updated.name(), updated.playbackUrl()));
            } catch (ResponseStatusException ignored) {
                // The video stream can run without the inference worker; face events resume when the worker is available.
            }
            return updated;
        }
        String dstUrl = properties.zlm().rtmpPushBase() + "/" + camera.streamName();
        String commandKey = null;
        if (isLocalVideoDevice(camera.sourceUrl())) {
            commandKey = "ffmpeg.v4l2_cmd";
            zlmClient.setServerConfig(commandKey, "%s -f v4l2 -i %s -an -c:v libx264 -preset veryfast -tune zerolatency -f flv %s");
        }
        Map<String, Object> response = zlmClient.addFfmpegSource(camera.sourceUrl(), dstUrl, commandKey);
        Object code = response.get("code");
        if (code != null && !code.toString().equals("0")) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "ZLMediaKit rejected source: " + response);
        }
        String ffmpegKey = responseKey(response);
        jdbcClient.sql("UPDATE cameras SET status = 'RUNNING', ffmpeg_key = :ffmpegKey, updated_at = now() WHERE id = :id")
                .param("id", id)
                .param("ffmpegKey", ffmpegKey)
                .update();
        CameraResponse updated = get(id);
        try {
            workerClient.startStream(new WorkerStartRequest(updated.id(), updated.name(), updated.playbackUrl()));
        } catch (ResponseStatusException ignored) {
            // The video stream can run without the inference worker; face events resume when the worker is available.
        }
        return updated;
    }

    @Transactional
    public CameraResponse stop(UUID id) {
        CameraResponse camera = get(id);
        try {
            workerClient.stopStream(new WorkerStopRequest(camera.id()));
        } catch (ResponseStatusException ignored) {
            // Stopping ZLMediaKit should still succeed if the inference worker is offline.
        }
        if (camera.ffmpegKey() != null && !camera.ffmpegKey().isBlank()) {
            zlmClient.deleteFfmpegSource(camera.ffmpegKey());
        }
        jdbcClient.sql("UPDATE cameras SET status = 'STOPPED', ffmpeg_key = NULL, updated_at = now() WHERE id = :id")
                .param("id", id)
                .update();
        return get(id);
    }

    public Map<String, Object> mediaList() {
        return zlmClient.mediaList();
    }

    private CameraResponse map(ResultSet rs, int rowNum) throws SQLException {
        String app = rs.getString("stream_app");
        String stream = rs.getString("stream_name");
        String playbackUrl = playbackUrl(rs.getString("source_url"), app, stream);
        return new CameraResponse(
                rs.getObject("id", UUID.class),
                rs.getString("name"),
                rs.getString("source_url"),
                app,
                stream,
                rs.getString("ffmpeg_key"),
                rs.getString("description"),
                rs.getString("status"),
                playbackUrl,
                rs.getObject("created_at", OffsetDateTime.class),
                rs.getObject("updated_at", OffsetDateTime.class),
                rs.getString("nvr_id"),
                rs.getString("nvr_channel"),
                rs.getString("nvr_track_id"),
                rs.getString("nvr_stream_type")
        );
    }

    private String clean(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return value.trim();
    }

    private boolean isLocalVideoDevice(String sourceUrl) {
        return sourceUrl.startsWith("/dev/video");
    }

    private boolean isPublishedMediaSource(String sourceUrl) {
        return sourceUrl.startsWith("rtmp://") || sourceUrl.startsWith("http://") || sourceUrl.startsWith("https://");
    }

    private String playbackUrl(String sourceUrl, String app, String stream) {
        if (sourceUrl.startsWith("rtmp://")) {
            int appIndex = sourceUrl.indexOf("/live/");
            if (appIndex >= 0) {
                String publishedStream = sourceUrl.substring(appIndex + "/live/".length());
                return properties.zlm().publicHttpUrl() + "/live/" + publishedStream + ".flv";
            }
        }
        if (sourceUrl.startsWith("http://") || sourceUrl.startsWith("https://")) {
            return sourceUrl;
        }
        return properties.zlm().publicHttpUrl() + "/" + app + "/" + stream + ".live.flv";
    }

    @SuppressWarnings("unchecked")
    private String responseKey(Map<String, Object> response) {
        Object key = response.get("key");
        if (key != null) {
            return key.toString();
        }
        Object data = response.get("data");
        if (data instanceof Map<?, ?> map) {
            Object nestedKey = map.get("key");
            if (nestedKey != null) {
                return nestedKey.toString();
            }
        }
        return null;
    }
}
