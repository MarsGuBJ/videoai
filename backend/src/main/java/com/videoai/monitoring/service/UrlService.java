package com.videoai.monitoring.service;

import org.springframework.stereotype.Service;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;

@Service
public class UrlService {
    public String fileUrl(String path) {
        if (path == null || path.isBlank()) {
            return null;
        }
        return "/api/files?path=" + URLEncoder.encode(path, StandardCharsets.UTF_8);
    }
}
