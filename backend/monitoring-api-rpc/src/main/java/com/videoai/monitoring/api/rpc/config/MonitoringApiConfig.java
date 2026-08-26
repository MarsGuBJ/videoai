package com.videoai.monitoring.api.rpc.config;

import org.springframework.cloud.openfeign.EnableFeignClients;
import org.springframework.context.annotation.Configuration;

/**
 * Enables the Feign proxies for the monitoring backend API contracts.
 * Registered as an auto-configuration via
 * {@code META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports}.
 */
@Configuration
@EnableFeignClients(basePackages = "com.videoai.monitoring.api.rpc.feign")
public class MonitoringApiConfig {
}
