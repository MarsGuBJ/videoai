package com.videoai.monitoring.core.service.impl;

import com.videoai.monitoring.common.dto.CloudPlatformCreateRequest;
import com.videoai.monitoring.common.dto.CloudPlatformUpdateRequest;
import com.videoai.monitoring.common.vo.CloudPlatformResponse;
import com.videoai.monitoring.core.dao.CloudPlatformDao;
import com.videoai.monitoring.core.entity.CloudPlatformEntity;
import com.videoai.monitoring.core.service.CloudPlatformService;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
public class CloudPlatformServiceImpl implements CloudPlatformService {
    private final CloudPlatformDao cloudPlatformDao;

    public CloudPlatformServiceImpl(CloudPlatformDao cloudPlatformDao) {
        this.cloudPlatformDao = cloudPlatformDao;
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
