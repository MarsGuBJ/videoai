package com.videoai.monitoring.core.service.impl;

import com.videoai.monitoring.core.config.VideoAiProperties;
import com.videoai.monitoring.core.service.FileStorageService;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.OffsetDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Base64;
import java.util.Locale;
import java.util.UUID;

@Service
public class FileStorageServiceImpl implements FileStorageService {
    private final Path faceDir;
    private final Path snapshotDir;

    public FileStorageServiceImpl(VideoAiProperties properties) throws IOException {
        this.faceDir = Path.of(properties.storage().faceDir()).toAbsolutePath().normalize();
        this.snapshotDir = Path.of(properties.storage().snapshotDir()).toAbsolutePath().normalize();
        Files.createDirectories(faceDir);
        Files.createDirectories(snapshotDir);
    }

    @Override
    public String saveFacePhoto(MultipartFile file) {
        String extension = extension(file.getOriginalFilename());
        Path path = faceDir.resolve(UUID.randomUUID() + extension);
        try {
            file.transferTo(path);
            return path.toString();
        } catch (IOException exception) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "Failed to save face photo", exception);
        }
    }

    @Override
    public String saveSnapshotBase64(String dataUrlOrBase64) {
        if (dataUrlOrBase64 == null || dataUrlOrBase64.isBlank()) {
            return null;
        }
        String base64 = dataUrlOrBase64;
        int comma = dataUrlOrBase64.indexOf(',');
        if (dataUrlOrBase64.startsWith("data:") && comma >= 0) {
            base64 = dataUrlOrBase64.substring(comma + 1);
        }
        byte[] bytes = Base64.getDecoder().decode(base64);
        String date = OffsetDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss", Locale.ROOT));
        Path path = snapshotDir.resolve(date + "-" + UUID.randomUUID() + ".jpg");
        try {
            Files.write(path, bytes);
            return path.toString();
        } catch (IOException exception) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "Failed to save event snapshot", exception);
        }
    }

    @Override
    public Path faceDir() {
        return faceDir;
    }

    @Override
    public Path snapshotDir() {
        return snapshotDir;
    }

    private String extension(String filename) {
        if (filename == null) {
            return ".jpg";
        }
        int index = filename.lastIndexOf('.');
        if (index < 0) {
            return ".jpg";
        }
        String extension = filename.substring(index).toLowerCase(Locale.ROOT);
        if (extension.equals(".jpg") || extension.equals(".jpeg") || extension.equals(".png") || extension.equals(".webp")) {
            return extension;
        }
        return ".jpg";
    }
}
