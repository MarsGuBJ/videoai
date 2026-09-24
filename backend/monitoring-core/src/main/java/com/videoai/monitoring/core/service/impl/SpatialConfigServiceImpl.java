package com.videoai.monitoring.core.service.impl;

import com.videoai.monitoring.common.dto.SpatialConfigUpdateRequest;
import com.videoai.monitoring.common.vo.SpatialConfigResponse;
import com.videoai.monitoring.core.dao.SpatialConfigDao;
import com.videoai.monitoring.core.entity.SpatialConfigEntity;
import com.videoai.monitoring.core.service.SpatialConfigService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.net.URI;
import java.time.OffsetDateTime;

/**
 * 空间服务配置读写。基址落库 spatial_config（单行 id=1），未配置时回退
 * application.yml 的 {@code videoai.spatial-info.base-url}。
 */
@Service
public class SpatialConfigServiceImpl implements SpatialConfigService {

    private final SpatialConfigDao spatialConfigDao;
    private final String fallbackBaseUrl;

    public SpatialConfigServiceImpl(SpatialConfigDao spatialConfigDao,
                                    @Value("${videoai.spatial-info.base-url:}") String fallbackBaseUrl) {
        this.spatialConfigDao = spatialConfigDao;
        this.fallbackBaseUrl = fallbackBaseUrl;
    }

    @Override
    public SpatialConfigResponse get() {
        SpatialConfigEntity entity = spatialConfigDao.selectById(SpatialConfigEntity.SINGLETON_ID);
        if (entity == null || isBlank(entity.getBaseUrl())) {
            return new SpatialConfigResponse(normalize(fallbackBaseUrl), null);
        }
        return new SpatialConfigResponse(normalize(entity.getBaseUrl()), entity.getUpdatedAt());
    }

    @Override
    @Transactional
    public SpatialConfigResponse save(SpatialConfigUpdateRequest request) {
        String baseUrl = normalize(request != null ? request.baseUrl() : null);
        if (baseUrl == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "空间服务地址不能为空");
        }
        requireAbsoluteHttpUrl(baseUrl);
        SpatialConfigEntity entity = new SpatialConfigEntity();
        entity.setId(SpatialConfigEntity.SINGLETON_ID);
        entity.setBaseUrl(baseUrl);
        entity.setUpdatedAt(OffsetDateTime.now());
        int updated = spatialConfigDao.updateById(entity);
        if (updated == 0) {
            spatialConfigDao.insert(entity);
        }
        return new SpatialConfigResponse(baseUrl, entity.getUpdatedAt());
    }

    @Override
    public String resolveBaseUrl() {
        SpatialConfigEntity entity = spatialConfigDao.selectById(SpatialConfigEntity.SINGLETON_ID);
        if (entity != null && !isBlank(entity.getBaseUrl())) {
            return normalize(entity.getBaseUrl());
        }
        return normalize(fallbackBaseUrl);
    }

    /** 校验必须是绝对 http/https 地址（feign RequestTemplate.target 也要求绝对地址）。 */
    private static void requireAbsoluteHttpUrl(String baseUrl) {
        URI uri;
        try {
            uri = URI.create(baseUrl);
        } catch (IllegalArgumentException exception) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "空间服务地址格式不正确");
        }
        String scheme = uri.getScheme();
        boolean httpScheme = scheme != null
                && (scheme.equalsIgnoreCase("http") || scheme.equalsIgnoreCase("https"));
        if (!httpScheme || isBlank(uri.getHost())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST,
                    "空间服务地址必须是 http/https 绝对地址，如 http://172.17.2.131:8080");
        }
    }

    /** 去掉首尾空白与结尾斜杠；空串返回 null。 */
    private static String normalize(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        while (trimmed.endsWith("/")) {
            trimmed = trimmed.substring(0, trimmed.length() - 1);
        }
        return trimmed.isEmpty() ? null : trimmed;
    }

    private static boolean isBlank(String value) {
        return value == null || value.isBlank();
    }
}
