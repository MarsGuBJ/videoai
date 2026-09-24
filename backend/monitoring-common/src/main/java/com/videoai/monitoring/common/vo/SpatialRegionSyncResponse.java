package com.videoai.monitoring.common.vo;

/**
 * 空间区域同步结果。
 *
 * <p>{@code success=false} 表示空间服务不可访问或返回失败——此时后端只记日志并返回该结果，
 * 不抛异常（区域管理页面照常可用）。{@code created} / {@code skipped} 为本次同步新增与
 * 已存在跳过的节点数，{@code total} 为参与判重的空间节点总数。</p>
 */
public record SpatialRegionSyncResponse(
        boolean success,
        String message,
        int created,
        int skipped,
        int total
) {
}
