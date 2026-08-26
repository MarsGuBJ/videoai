package com.videoai.monitoring.core.client;

import com.videoai.monitoring.common.dto.WorkerStartRequest;
import com.videoai.monitoring.common.dto.WorkerStopRequest;
import com.videoai.monitoring.common.vo.EmbeddingResponse;
import com.videoai.monitoring.common.vo.WorkerStatusResponse;
import com.videoai.monitoring.core.config.VideoAiProperties;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;
import org.springframework.web.server.ResponseStatusException;

import java.nio.file.Path;

@Component
public class WorkerClient {
    private final RestClient restClient;
    private final VideoAiProperties properties;

    public WorkerClient(RestClient restClient, VideoAiProperties properties) {
        this.restClient = restClient;
        this.properties = properties;
    }

    public float[] extractEmbedding(Path imagePath) {
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("file", new FileSystemResource(imagePath));
        try {
            EmbeddingResponse response = restClient.post()
                    .uri(properties.worker().url() + "/v1/faces/extract")
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .body(body)
                    .retrieve()
                    .body(EmbeddingResponse.class);
            if (response == null || response.embedding() == null) {
                throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Worker returned no embedding");
            }
            return response.embedding();
        } catch (ResponseStatusException exception) {
            throw exception;
        } catch (Exception exception) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Failed to extract face embedding: " + exception.getMessage(), exception);
        }
    }

    public void startStream(WorkerStartRequest request) {
        postNoBody("/v1/streams/start", request, "Failed to start worker stream");
    }

    public void stopStream(WorkerStopRequest request) {
        postNoBody("/v1/streams/stop", request, "Failed to stop worker stream");
    }

    public WorkerStatusResponse status() {
        try {
            WorkerStatusResponse response = restClient.get()
                    .uri(properties.worker().url() + "/v1/streams")
                    .retrieve()
                    .body(WorkerStatusResponse.class);
            return response == null ? new WorkerStatusResponse(java.util.Map.of()) : response;
        } catch (Exception exception) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Failed to read worker status: " + exception.getMessage(), exception);
        }
    }

    private void postNoBody(String path, Object body, String message) {
        try {
            restClient.post()
                    .uri(properties.worker().url() + path)
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(body)
                    .retrieve()
                    .toBodilessEntity();
        } catch (Exception exception) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, message + ": " + exception.getMessage(), exception);
        }
    }
}
