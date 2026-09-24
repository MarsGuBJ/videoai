package com.videoai.monitoring.core.client;

import feign.RequestInterceptor;
import org.springframework.context.annotation.Bean;

/**
 * {@link SpatialInfoFeign} 的 Feign 配置：用请求拦截器把目标地址改为界面里配置的空间服务基址。
 *
 * <p>不做 {@code @Configuration} 标注，避免被组件扫描成全局配置；仅由
 * {@code @FeignClient(configuration = ...)} 在客户端子上下文中加载。</p>
 */
public class SpatialInfoFeignConfig {

    @Bean
    public RequestInterceptor spatialInfoTargetInterceptor() {
        return template -> {
            String baseUrl = SpatialBaseUrlHolder.get();
            // target() 只接受绝对地址；未设置时沿用 @FeignClient(url=...) 的默认值
            if (baseUrl != null && !baseUrl.isBlank()) {
                template.target(baseUrl);
            }
        };
    }
}
