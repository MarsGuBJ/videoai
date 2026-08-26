package com.videoai.monitoring.core.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.videoai.monitoring.common.dto.ModelRegisterRequest;
import com.videoai.monitoring.common.vo.ModelConfigResponse;
import com.videoai.monitoring.common.vo.ModelResponse;
import com.videoai.monitoring.common.vo.TritonModelStatus;
import com.videoai.monitoring.core.client.TritonClient;
import com.videoai.monitoring.core.dao.ModelRegistryDao;
import com.videoai.monitoring.core.entity.ModelRegistryEntity;
import com.videoai.monitoring.core.service.ModelRegistryService;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
public class ModelRegistryServiceImpl implements ModelRegistryService {
    private final ModelRegistryDao modelRegistryDao;
    private final TritonClient tritonClient;

    public ModelRegistryServiceImpl(ModelRegistryDao modelRegistryDao, TritonClient tritonClient) {
        this.modelRegistryDao = modelRegistryDao;
        this.tritonClient = tritonClient;
    }

    @Override
    public List<ModelResponse> list() {
        Map<String, TritonModelStatus> tritonStatus = tritonClient.repositoryIndex().stream()
                .filter(status -> status.name() != null)
                .collect(Collectors.toMap(TritonModelStatus::name, Function.identity(), (a, b) -> a));
        List<ModelResponse> local = modelRegistryDao.selectAllOrdered().stream().map(this::toResponse).toList();
        for (ModelResponse model : local) {
            TritonModelStatus status = tritonStatus.get(model.name());
            if (status != null && status.state() != null && !status.state().equals(model.state())) {
                modelRegistryDao.updateStateById(model.id(), status.state());
            }
        }
        return modelRegistryDao.selectAllOrdered().stream().map(this::toResponse).toList();
    }

    @Override
    @Transactional
    public ModelResponse register(ModelRegisterRequest request) {
        ModelRegistryEntity entity = new ModelRegistryEntity();
        entity.setId(UUID.randomUUID());
        entity.setName(request.name());
        entity.setDisplayName(request.displayName());
        entity.setRepositoryPath(request.repositoryPath());
        entity.setModelType(request.modelType());
        entity.setDescription(request.description());
        modelRegistryDao.upsert(entity);
        return getByName(request.name());
    }

    @Override
    public ModelResponse load(String name) {
        ensureExists(name);
        tritonClient.load(name);
        updateState(name, "LOADING");
        return getByName(name);
    }

    @Override
    public ModelResponse unload(String name) {
        ensureExists(name);
        tritonClient.unload(name);
        updateState(name, "UNLOADING");
        return getByName(name);
    }

    @Override
    public ModelConfigResponse config(String name) {
        ensureExists(name);
        return tritonClient.config(name);
    }

    private void ensureExists(String name) {
        Long count = modelRegistryDao.selectCount(new QueryWrapper<ModelRegistryEntity>().eq("name", name));
        if (count == null || count == 0) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Model not registered");
        }
    }

    private ModelResponse getByName(String name) {
        return toResponse(modelRegistryDao.selectOne(new QueryWrapper<ModelRegistryEntity>().eq("name", name)));
    }

    private void updateState(String name, String state) {
        modelRegistryDao.updateStateByName(name, state);
    }

    private ModelResponse toResponse(ModelRegistryEntity entity) {
        return new ModelResponse(
                entity.getId(),
                entity.getName(),
                entity.getDisplayName(),
                entity.getRepositoryPath(),
                entity.getModelType(),
                entity.getDescription(),
                entity.getState(),
                entity.getCreatedAt(),
                entity.getUpdatedAt()
        );
    }
}
