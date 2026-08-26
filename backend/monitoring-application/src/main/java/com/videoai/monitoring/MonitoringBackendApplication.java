package com.videoai.monitoring;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication(scanBasePackages = "com.videoai.monitoring")
@ConfigurationPropertiesScan(basePackages = "com.videoai.monitoring.core.config")
@EnableScheduling
@MapperScan("com.videoai.monitoring.core.dao")
public class MonitoringBackendApplication {
    public static void main(String[] args) {
        SpringApplication.run(MonitoringBackendApplication.class, args);
    }
}
