package com.videoai.monitoring.core.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.videoai.monitoring.common.dto.FaceUpdateRequest;
import com.videoai.monitoring.common.vo.FaceProfileResponse;
import com.videoai.monitoring.common.vo.MatchCandidate;
import com.videoai.monitoring.core.client.WorkerClient;
import com.videoai.monitoring.core.dao.FaceProfileDao;
import com.videoai.monitoring.core.entity.FaceProfileEntity;
import com.videoai.monitoring.core.service.FaceProfileService;
import com.videoai.monitoring.core.service.FileStorageService;
import com.videoai.monitoring.core.support.UrlService;
import com.videoai.monitoring.core.support.VectorSql;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.nio.file.Path;
import java.util.Comparator;
import java.util.List;
import java.util.UUID;

@Service
public class FaceProfileServiceImpl implements FaceProfileService {
    private final FaceProfileDao faceProfileDao;
    private final WorkerClient workerClient;
    private final FileStorageService fileStorageService;
    private final VectorSql vectorSql;
    private final UrlService urlService;

    public FaceProfileServiceImpl(
            FaceProfileDao faceProfileDao,
            WorkerClient workerClient,
            FileStorageService fileStorageService,
            VectorSql vectorSql,
            UrlService urlService
    ) {
        this.faceProfileDao = faceProfileDao;
        this.workerClient = workerClient;
        this.fileStorageService = fileStorageService;
        this.vectorSql = vectorSql;
        this.urlService = urlService;
    }

    @Override
    public List<FaceProfileResponse> list() {
        return faceProfileDao.selectAllOrdered().stream().map(this::toResponse).toList();
    }

    @Override
    public FaceProfileResponse get(UUID id) {
        FaceProfileEntity entity = faceProfileDao.selectById(id);
        if (entity == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Face profile not found");
        }
        return toResponse(entity);
    }

    @Override
    @Transactional
    public FaceProfileResponse create(String name, String description, MultipartFile photo) {
        if (photo == null || photo.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "photo is required");
        }
        String photoPath = fileStorageService.saveFacePhoto(photo);
        float[] embedding = vectorSql.normalize(workerClient.extractEmbedding(Path.of(photoPath)));
        UUID id = UUID.randomUUID();
        FaceProfileEntity entity = new FaceProfileEntity();
        entity.setId(id);
        entity.setName(name);
        entity.setDescription(description);
        entity.setPhotoPath(photoPath);
        entity.setEmbedding(vectorSql.toVectorLiteral(embedding));
        faceProfileDao.insert(entity);
        return get(id);
    }

    @Override
    @Transactional
    public FaceProfileResponse update(UUID id, FaceUpdateRequest request, MultipartFile photo) {
        get(id);
        if (photo != null && !photo.isEmpty()) {
            String photoPath = fileStorageService.saveFacePhoto(photo);
            float[] embedding = vectorSql.normalize(workerClient.extractEmbedding(Path.of(photoPath)));
            FaceProfileEntity entity = new FaceProfileEntity();
            entity.setId(id);
            entity.setName(request.name());
            entity.setDescription(request.description());
            entity.setPhotoPath(photoPath);
            entity.setEmbedding(vectorSql.toVectorLiteral(embedding));
            faceProfileDao.updateWithPhoto(entity);
        } else {
            FaceProfileEntity entity = new FaceProfileEntity();
            entity.setId(id);
            entity.setName(request.name());
            entity.setDescription(request.description());
            faceProfileDao.updateWithoutPhoto(entity);
        }
        return get(id);
    }

    @Override
    @Transactional
    public void delete(UUID id) {
        faceProfileDao.deleteById(id);
    }

    @Override
    public MatchCandidate match(float[] embedding, double threshold) {
        float[] normalized = vectorSql.normalize(embedding);
        return faceProfileDao.selectList(Wrappers.emptyWrapper())
                .stream()
                .map(entity -> new MatchCandidate(
                        entity.getId(),
                        entity.getName(),
                        entity.getDescription(),
                        entity.getPhotoPath(),
                        cosine(normalized, parseEmbedding(entity.getEmbedding()))
                ))
                .filter(candidate -> candidate.similarity() >= threshold)
                .max(Comparator.comparingDouble(MatchCandidate::similarity))
                .orElse(null);
    }

    private FaceProfileResponse toResponse(FaceProfileEntity entity) {
        return new FaceProfileResponse(
                entity.getId(),
                entity.getName(),
                entity.getDescription(),
                urlService.fileUrl(entity.getPhotoPath()),
                entity.getCreatedAt(),
                entity.getUpdatedAt()
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
