package com.videoai.monitoring.core.service;

import org.springframework.web.multipart.MultipartFile;

import java.nio.file.Path;

public interface FileStorageService {

    String saveFacePhoto(MultipartFile file);

    String saveSnapshotBase64(String dataUrlOrBase64);

    Path faceDir();

    Path snapshotDir();
}
