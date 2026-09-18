package com.videoai.monitoring.common.dto;

/**
 * Upsert request body for a GB/T 28181 cascade (上级联) server entry.
 * Simplified model: name / SIP ID / SIP IP / SIP port / username / password.
 * sipId 可空（级联服务器国标编码，云平台同步 Catalog 查询时必填）。
 */
public record Gb28181EntryRequest(
        String name,
        String sipId,
        String sipIp,
        String sipPort,
        String username,
        String password
) {
}
