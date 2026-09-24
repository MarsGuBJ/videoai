package com.videoai.monitoring.api;

import com.videoai.monitoring.common.dto.SpatialConfigUpdateRequest;
import com.videoai.monitoring.common.vo.SpatialConfigResponse;
import com.videoai.monitoring.common.vo.SpatialRegionSyncResponse;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;

/**
 * 空间区域同步 API contract。Implemented by a controller in monitoring-core。
 *
 * <p>从空间服务 {@code /spatialServer/spatialInfo/tree} 读取园区/区域/楼栋/楼层，
 * 只新增区域树中缺失的节点，已存在的区域结构不做任何修改；空间服务基址可在界面配置。</p>
 */
@RequestMapping("/api/regions")
public interface SpatialRegionApi {

    /** 读取当前空间服务基址（供区域管理弹窗回填输入框）。 */
    @GetMapping("/spatial-config")
    SpatialConfigResponse getSpatialConfig();

    /** 保存空间服务基址（落库，后续同步区域树使用该地址）。 */
    @PutMapping("/spatial-config")
    SpatialConfigResponse saveSpatialConfig(@Valid @RequestBody SpatialConfigUpdateRequest request);

    /** 从空间服务同步区域树：只新增缺失节点，接口不可达时只记日志并返回 success=false。 */
    @PostMapping("/sync-spatial")
    SpatialRegionSyncResponse syncSpatial();
}
