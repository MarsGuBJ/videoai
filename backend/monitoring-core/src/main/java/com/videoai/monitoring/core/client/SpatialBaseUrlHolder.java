package com.videoai.monitoring.core.client;

/**
 * 本次线程调用空间服务使用的基址（来自 spatial_config 配置）。
 *
 * <p>Feign 的 {@code @FeignClient(url=...)} 在启动时静态解析，无法跟随界面修改；
 * 因此由 {@link SpatialInfoFeignConfig} 的请求拦截器读取本 holder，在每次调用前用
 * {@code RequestTemplate.target(baseUrl)} 覆盖目标地址。调用方必须在 finally 中
 * {@link #clear()}，避免线程复用串地址。</p>
 */
public final class SpatialBaseUrlHolder {

    private static final ThreadLocal<String> CURRENT = new ThreadLocal<>();

    private SpatialBaseUrlHolder() {
    }

    public static void set(String baseUrl) {
        CURRENT.set(baseUrl);
    }

    public static String get() {
        return CURRENT.get();
    }

    public static void clear() {
        CURRENT.remove();
    }
}
