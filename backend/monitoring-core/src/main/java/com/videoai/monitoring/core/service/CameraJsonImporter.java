package com.videoai.monitoring.core.service;

import org.springframework.boot.ApplicationRunner;

/**
 * One-shot import of the Python backend-lite cameras.json into Postgres when the
 * cameras table is still empty. Failures are logged and never block startup.
 */
public interface CameraJsonImporter extends ApplicationRunner {
}
