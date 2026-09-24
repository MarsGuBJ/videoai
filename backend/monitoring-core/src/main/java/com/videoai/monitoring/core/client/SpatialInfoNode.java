package com.videoai.monitoring.core.client;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

import java.util.List;

/**
 * 空间树单个节点。只声明同步区域所需的字段，其余字段（坐标/面积/房间等）忽略。
 *
 * <ul>
 *   <li>{@code spatialName}：区域名称，写入 {@code regions.name}</li>
 *   <li>{@code children}：子节点（园区/区域/楼栋/楼层）</li>
 *   <li>{@code type}：DISTRICT / BUILD / FLOOR，仅用于日志排查</li>
 * </ul>
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record SpatialInfoNode(
        String id,
        String spatialName,
        String spatialCode,
        String parentId,
        Integer sort,
        String type,
        List<SpatialInfoNode> children
) {
}
