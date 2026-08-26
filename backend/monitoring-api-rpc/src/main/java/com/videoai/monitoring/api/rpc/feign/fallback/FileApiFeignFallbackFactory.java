package com.videoai.monitoring.api.rpc.feign.fallback;

import com.videoai.monitoring.api.rpc.feign.FileApiFeign;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.openfeign.FallbackFactory;
import org.springframework.stereotype.Component;

/**
 * Fallback for {@link FileApiFeign}. The feign interface declares no methods
 * (the file endpoint is a streaming download), so the fallback is an empty
 * implementation.
 */
@Slf4j
@Component
public class FileApiFeignFallbackFactory implements FallbackFactory<FileApiFeign> {
    @Override
    public FileApiFeign create(Throwable cause) {
        log.error("FileApi feign call failed, fallback triggered", cause);
        return new FileApiFeign() {
        };
    }
}
