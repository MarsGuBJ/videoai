package com.videoai.monitoring.service;

import com.videoai.monitoring.client.TritonClient;
import com.videoai.monitoring.dto.ModelDtos.ModelConfigResponse;
import com.videoai.monitoring.dto.ModelDtos.ModelRegisterRequest;
import com.videoai.monitoring.dto.ModelDtos.ModelResponse;
import com.videoai.monitoring.dto.ModelDtos.TritonModelStatus;
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
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
public class ModelRegistryService {
    private final JdbcClient jdbcClient;
    private final TritonClient tritonClient;

    public ModelRegistryService(JdbcClient jdbcClient, TritonClient tritonClient) {
        this.jdbcClient = jdbcClient;
        this.tritonClient = tritonClient;
    }

    public List<ModelResponse> list() {
        Map<String, TritonModelStatus> tritonStatus = tritonClient.repositoryIndex().stream()
                .filter(status -> status.name() != null)
                .collect(Collectors.toMap(TritonModelStatus::name, Function.identity(), (a, b) -> a));
        List<ModelResponse> local = jdbcClient.sql("SELECT * FROM model_registry ORDER BY created_at DESC")
                .query(this::map)
                .list();
        for (ModelResponse model : local) {
            TritonModelStatus status = tritonStatus.get(model.name());
            if (status != null && status.state() != null && !status.state().equals(model.state())) {
                jdbcClient.sql("UPDATE model_registry SET state = :state, updated_at = now() WHERE id = :id")
                        .param("state", status.state())
                        .param("id", model.id())
                        .update();
            }
        }
        return jdbcClient.sql("SELECT * FROM model_registry ORDER BY created_at DESC")
                .query(this::map)
                .list();
    }

    @Transactional
    public ModelResponse register(ModelRegisterRequest request) {
        UUID id = UUID.randomUUID();
        jdbcClient.sql("""
                        INSERT INTO model_registry
                        (id, name, display_name, repository_path, model_type, description)
                        VALUES (:id, :name, :displayName, :repositoryPath, :modelType, :description)
                        ON CONFLICT (name) DO UPDATE
                        SET display_name = excluded.display_name,
                            repository_path = excluded.repository_path,
                            model_type = excluded.model_type,
                            description = excluded.description,
                            updated_at = now()
                        """)
                .param("id", id)
                .param("name", request.name())
                .param("displayName", request.displayName())
                .param("repositoryPath", request.repositoryPath())
                .param("modelType", request.modelType())
                .param("description", request.description())
                .update();
        return getByName(request.name());
    }

    public ModelResponse load(String name) {
        ensureExists(name);
        tritonClient.load(name);
        updateState(name, "LOADING");
        return getByName(name);
    }

    public ModelResponse unload(String name) {
        ensureExists(name);
        tritonClient.unload(name);
        updateState(name, "UNLOADING");
        return getByName(name);
    }

    public ModelConfigResponse config(String name) {
        ensureExists(name);
        return tritonClient.config(name);
    }

    private void ensureExists(String name) {
        jdbcClient.sql("SELECT COUNT(*) FROM model_registry WHERE name = :name")
                .param("name", name)
                .query(Integer.class)
                .optional()
                .filter(count -> count > 0)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Model not registered"));
    }

    private ModelResponse getByName(String name) {
        return jdbcClient.sql("SELECT * FROM model_registry WHERE name = :name")
                .param("name", name)
                .query(this::map)
                .single();
    }

    private void updateState(String name, String state) {
        jdbcClient.sql("UPDATE model_registry SET state = :state, updated_at = now() WHERE name = :name")
                .param("name", name)
                .param("state", state)
                .update();
    }

    private ModelResponse map(ResultSet rs, int rowNum) throws SQLException {
        return new ModelResponse(
                rs.getObject("id", UUID.class),
                rs.getString("name"),
                rs.getString("display_name"),
                rs.getString("repository_path"),
                rs.getString("model_type"),
                rs.getString("description"),
                rs.getString("state"),
                rs.getObject("created_at", OffsetDateTime.class),
                rs.getObject("updated_at", OffsetDateTime.class)
        );
    }
}

