package com.videoai.monitoring.core.service.impl;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.videoai.monitoring.core.config.VideoAiProperties;
import com.videoai.monitoring.core.dao.CameraDao;
import com.videoai.monitoring.core.entity.CameraEntity;
import com.videoai.monitoring.core.service.CameraJsonImporter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.OffsetDateTime;
import java.util.UUID;

@Component
@Order(1)
public class CameraJsonImporterImpl implements CameraJsonImporter {
    private static final Logger log = LoggerFactory.getLogger(CameraJsonImporterImpl.class);

    private final CameraDao cameraDao;
    private final VideoAiProperties properties;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public CameraJsonImporterImpl(CameraDao cameraDao, VideoAiProperties properties) {
        this.cameraDao = cameraDao;
        this.properties = properties;
    }

    @Override
    public void run(ApplicationArguments args) {
        try {
            importIfEmpty();
        } catch (Exception exception) {
            log.warn("Camera JSON import failed (startup continues)", exception);
        }
    }

    private void importIfEmpty() throws Exception {
        Long count = cameraDao.selectCount(null);
        if (count != null && count > 0) {
            return;
        }
        Path file = Path.of(properties.storage().cameraDir()).resolve("cameras.json");
        if (!Files.isRegularFile(file)) {
            return;
        }
        JsonNode root = objectMapper.readTree(file.toFile());
        if (!root.isArray()) {
            log.warn("Camera JSON import skipped: {} is not an array", file);
            return;
        }
        int imported = 0;
        for (JsonNode node : root) {
            insert(node);
            imported++;
        }
        log.info("Imported {} cameras from {}", imported, file);
    }

    private void insert(JsonNode node) {
        CameraEntity entity = new CameraEntity();
        entity.setId(UUID.fromString(node.path("id").asText()));
        entity.setName(node.path("name").asText());
        entity.setSourceUrl(node.path("sourceUrl").asText());
        entity.setStreamApp(text(node, "streamApp", "live"));
        entity.setStreamName(node.path("streamName").asText());
        entity.setFfmpegKey(text(node, "ffmpegKey", null));
        entity.setDescription(text(node, "description", null));
        entity.setArea(text(node, "area", null));
        entity.setStatus(text(node, "status", "STOPPED"));
        entity.setCreatedAt(timestamp(node, "createdAt"));
        entity.setUpdatedAt(timestamp(node, "updatedAt"));
        entity.setNvrId(text(node, "nvrId", null));
        entity.setNvrChannel(text(node, "nvrChannel", null));
        entity.setNvrTrackId(text(node, "nvrTrackId", null));
        entity.setNvrStreamType(text(node, "nvrStreamType", null));
        entity.setProtocol(text(node, "protocol", null));
        entity.setVendor(text(node, "vendor", null));
        entity.setIp(text(node, "ip", null));
        entity.setPort(text(node, "port", null));
        entity.setUsername(text(node, "username", null));
        entity.setPassword(text(node, "password", null));
        entity.setDeviceCode(text(node, "deviceCode", null));
        entity.setSerialNumber(text(node, "serialNumber", null));
        cameraDao.insertIgnore(entity);
    }

    private String text(JsonNode node, String field, String fallback) {
        JsonNode value = node.path(field);
        if (value.isMissingNode() || value.isNull()) {
            return fallback;
        }
        return value.asText();
    }

    private OffsetDateTime timestamp(JsonNode node, String field) {
        String value = text(node, field, null);
        return value != null ? OffsetDateTime.parse(value) : OffsetDateTime.now();
    }
}
