package com.videoai.monitoring.core.client;

import com.videoai.monitoring.common.vo.ModelConfigResponse;
import com.videoai.monitoring.common.vo.TritonModelStatus;
import com.videoai.monitoring.core.config.VideoAiProperties;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.server.ResponseStatusException;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Component
public class TritonClient {
    private final RestClient restClient;
    private final VideoAiProperties properties;

    public TritonClient(RestClient restClient, VideoAiProperties properties) {
        this.restClient = restClient;
        this.properties = properties;
    }

    public List<TritonModelStatus> repositoryIndex() {
        try {
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> response = restClient.post()
                    .uri(properties.triton().httpUrl() + "/v2/repository/index")
                    .body(Map.of("ready", false))
                    .retrieve()
                    .body(List.class);
            if (response == null) {
                return List.of();
            }
            List<TritonModelStatus> statuses = new ArrayList<>();
            for (Map<String, Object> item : response) {
                statuses.add(new TritonModelStatus(
                        string(item.get("name")),
                        string(item.get("version")),
                        string(item.get("state")),
                        string(item.get("reason"))
                ));
            }
            return statuses;
        } catch (Exception exception) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Failed to query Triton repository: " + exception.getMessage(), exception);
        }
    }

    public void load(String modelName) {
        postRepository(modelName, "load", "Failed to load Triton model");
    }

    public void unload(String modelName) {
        postRepository(modelName, "unload", "Failed to unload Triton model");
    }

    public ModelConfigResponse config(String modelName) {
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> response = restClient.get()
                    .uri(properties.triton().httpUrl() + "/v2/models/" + modelName + "/config")
                    .retrieve()
                    .body(Map.class);
            return new ModelConfigResponse(modelName, response == null ? Map.of() : response);
        } catch (Exception exception) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Failed to read Triton model config: " + exception.getMessage(), exception);
        }
    }

    private void postRepository(String modelName, String action, String message) {
        try {
            restClient.post()
                    .uri(properties.triton().httpUrl() + "/v2/repository/models/" + modelName + "/" + action)
                    .body(Map.of())
                    .retrieve()
                    .toBodilessEntity();
        } catch (Exception exception) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, message + ": " + exception.getMessage(), exception);
        }
    }

    private String string(Object value) {
        return value == null ? null : value.toString();
    }
}
