package com.videoai.monitoring.core.client;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

/**
 * 空间服务（spatialServer）Feign 客户端：读取空间区域树。
 *
 * <p>实际调用的基址由界面配置（spatial_config 表）在运行时通过
 * {@link SpatialInfoFeignConfig} 的拦截器覆盖；{@code url} 只是
 * {@code @FeignClient} 的占位默认值（避免启用负载均衡），不可达时由调用方
 * 捕获异常并记日志，不影响区域管理页面。</p>
 */
@FeignClient(name = "spatial-info", url = "${videoai.spatial-info.base-url:http://127.0.0.1:9}",
        configuration = SpatialInfoFeignConfig.class)
public interface SpatialInfoFeign {

    /**
     * 查询空间树。{@code hasOther=true} 时楼层节点才带有 {@code children}（楼栋/楼层完整层级），
     * 房间信息在 {@code roomInfoList} 中，本客户端不同步房间。
     */
    @GetMapping("/spatialServer/spatialInfo/tree")
    SpatialInfoTreeResponse tree(@RequestParam("hasOther") boolean hasOther);
}
