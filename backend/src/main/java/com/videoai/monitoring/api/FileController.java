package com.videoai.monitoring.api;

import com.videoai.monitoring.service.FileStorageService;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.nio.file.Files;
import java.nio.file.Path;

@RestController
public class FileController {
    private final FileStorageService fileStorageService;

    public FileController(FileStorageService fileStorageService) {
        this.fileStorageService = fileStorageService;
    }

    @GetMapping("/api/files")
    ResponseEntity<Resource> read(@RequestParam String path) {
        Path requested = Path.of(path).toAbsolutePath().normalize();
        if (!requested.startsWith(fileStorageService.faceDir()) && !requested.startsWith(fileStorageService.snapshotDir())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "File is outside configured storage");
        }
        if (!Files.exists(requested) || !Files.isRegularFile(requested)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "File not found");
        }
        MediaType mediaType = mediaType(requested);
        return ResponseEntity.ok()
                .contentType(mediaType)
                .body(new FileSystemResource(requested));
    }

    private MediaType mediaType(Path path) {
        String filename = path.getFileName().toString().toLowerCase();
        if (filename.endsWith(".png")) {
            return MediaType.IMAGE_PNG;
        }
        if (filename.endsWith(".webp")) {
            return MediaType.parseMediaType("image/webp");
        }
        return MediaType.IMAGE_JPEG;
    }
}

