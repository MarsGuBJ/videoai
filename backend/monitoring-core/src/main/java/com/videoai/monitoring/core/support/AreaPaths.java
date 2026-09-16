package com.videoai.monitoring.core.support;

import java.util.Arrays;
import java.util.stream.Collectors;

/**
 * cameras.area 路径规范化：按 "/" 分段、逐段 trim、丢弃空段后以 " / " 连接，
 * 与区域树节点完整路径的口径一致（区域设备计数与前缀替换都依赖该口径）。
 */
public final class AreaPaths {

    private AreaPaths() {
    }

    /** 规范化区域路径；入参为 null 或规范化后为空（如 "///"）时返回 null。 */
    public static String normalize(String area) {
        if (area == null) {
            return null;
        }
        String normalized = Arrays.stream(area.split("/"))
                .map(String::trim)
                .filter(part -> !part.isEmpty())
                .collect(Collectors.joining(" / "));
        return normalized.isEmpty() ? null : normalized;
    }
}
