package com.videoai.monitoring.core.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {
    @Bean
    OpenAPI monitoringOpenAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("VideoAI Monitoring API")
                        .version("0.1.0")
                        .description("视觉大模型监控平台后端 API 文档"));
    }
}
