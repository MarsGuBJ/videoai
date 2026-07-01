package com.videoai.monitoring.service;

import com.videoai.monitoring.client.WorkerClient;
import com.videoai.monitoring.db.VectorSql;
import com.videoai.monitoring.dto.FaceDtos.FaceProfileResponse;
import com.videoai.monitoring.dto.FaceDtos.FaceUpdateRequest;
import com.videoai.monitoring.dto.FaceDtos.MatchCandidate;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.nio.file.Path;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

@Service
public class FaceProfileService {
    private final JdbcClient jdbcClient;
    private final WorkerClient workerClient;
    private final FileStorageService fileStorageService;
    private final VectorSql vectorSql;
    private final UrlService urlService;

    public FaceProfileService(
            JdbcClient jdbcClient,
            WorkerClient workerClient,
            FileStorageService fileStorageService,
            VectorSql vectorSql,
            UrlService urlService
    ) {
        this.jdbcClient = jdbcClient;
        this.workerClient = workerClient;
        this.fileStorageService = fileStorageService;
        this.vectorSql = vectorSql;
        this.urlService = urlService;
    }

    public List<FaceProfileResponse> list() {
        return jdbcClient.sql("SELECT * FROM face_profiles ORDER BY created_at DESC")
                .query(this::map)
                .list();
    }

    public FaceProfileResponse get(UUID id) {
        return jdbcClient.sql("SELECT * FROM face_profiles WHERE id = :id")
                .param("id", id)
                .query(this::map)
                .optional()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Face profile not found"));
    }

    @Transactional
    public FaceProfileResponse create(String name, String description, MultipartFile photo) {
        if (photo == null || photo.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "photo is required");
        }
        String photoPath = fileStorageService.saveFacePhoto(photo);
        float[] embedding = vectorSql.normalize(workerClient.extractEmbedding(Path.of(photoPath)));
        UUID id = UUID.randomUUID();
        jdbcClient.sql("""
                        INSERT INTO face_profiles (id, name, description, photo_path, embedding)
                        VALUES (:id, :name, :description, :photoPath, :embedding)
                        """)
                .param("id", id)
                .param("name", name)
                .param("description", description)
                .param("photoPath", photoPath)
                .param("embedding", vectorSql.toVectorLiteral(embedding))
                .update();
        return get(id);
    }

    @Transactional
    public FaceProfileResponse update(UUID id, FaceUpdateRequest request, MultipartFile photo) {
        get(id);
        if (photo != null && !photo.isEmpty()) {
            String photoPath = fileStorageService.saveFacePhoto(photo);
            float[] embedding = vectorSql.normalize(workerClient.extractEmbedding(Path.of(photoPath)));
            jdbcClient.sql("""
                            UPDATE face_profiles
                            SET name = :name, description = :description, photo_path = :photoPath,
                                embedding = :embedding, updated_at = now()
                            WHERE id = :id
                            """)
                    .param("id", id)
                    .param("name", request.name())
                    .param("description", request.description())
                    .param("photoPath", photoPath)
                    .param("embedding", vectorSql.toVectorLiteral(embedding))
                    .update();
        } else {
            jdbcClient.sql("""
                            UPDATE face_profiles
                            SET name = :name, description = :description, updated_at = now()
                            WHERE id = :id
                            """)
                    .param("id", id)
                    .param("name", request.name())
                    .param("description", request.description())
                    .update();
        }
        return get(id);
    }

    @Transactional
    public void delete(UUID id) {
        jdbcClient.sql("DELETE FROM face_profiles WHERE id = :id")
                .param("id", id)
                .update();
    }

    public MatchCandidate match(float[] embedding, double threshold) {
        float[] normalized = vectorSql.normalize(embedding);
        return jdbcClient.sql("SELECT id, name, description, photo_path, embedding FROM face_profiles")
                .query((rs, rowNum) -> matchMap(rs, normalized))
                .list()
                .stream()
                .filter(candidate -> candidate.similarity() >= threshold)
                .max(java.util.Comparator.comparingDouble(MatchCandidate::similarity))
                .orElse(null);
    }

    private FaceProfileResponse map(ResultSet rs, int rowNum) throws SQLException {
        return new FaceProfileResponse(
                rs.getObject("id", UUID.class),
                rs.getString("name"),
                rs.getString("description"),
                urlService.fileUrl(rs.getString("photo_path")),
                rs.getObject("created_at", OffsetDateTime.class),
                rs.getObject("updated_at", OffsetDateTime.class)
        );
    }

    private MatchCandidate matchMap(ResultSet rs, int rowNum) throws SQLException {
        return new MatchCandidate(
                rs.getObject("id", UUID.class),
                rs.getString("name"),
                rs.getString("description"),
                rs.getString("photo_path"),
                rs.getDouble("similarity")
        );
    }

    private MatchCandidate matchMap(ResultSet rs, float[] query) throws SQLException {
        float[] candidate = parseEmbedding(rs.getString("embedding"));
        return new MatchCandidate(
                rs.getObject("id", UUID.class),
                rs.getString("name"),
                rs.getString("description"),
                rs.getString("photo_path"),
                cosine(query, candidate)
        );
    }

    private float[] parseEmbedding(String value) {
        String clean = value.replace("[", "").replace("]", "");
        String[] parts = clean.split(",");
        float[] embedding = new float[parts.length];
        for (int i = 0; i < parts.length; i++) {
            embedding[i] = Float.parseFloat(parts[i]);
        }
        return embedding;
    }

    private double cosine(float[] a, float[] b) {
        int length = Math.min(a.length, b.length);
        double dot = 0.0;
        double normA = 0.0;
        double normB = 0.0;
        for (int i = 0; i < length; i++) {
            dot += a[i] * b[i];
            normA += a[i] * a[i];
            normB += b[i] * b[i];
        }
        if (normA == 0.0 || normB == 0.0) {
            return 0.0;
        }
        return dot / (Math.sqrt(normA) * Math.sqrt(normB));
    }
}
