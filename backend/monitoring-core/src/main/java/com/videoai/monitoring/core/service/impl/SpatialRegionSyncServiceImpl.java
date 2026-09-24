package com.videoai.monitoring.core.service.impl;

import com.videoai.monitoring.common.vo.SpatialRegionSyncResponse;
import com.videoai.monitoring.core.client.SpatialBaseUrlHolder;
import com.videoai.monitoring.core.client.SpatialInfoFeign;
import com.videoai.monitoring.core.client.SpatialInfoNode;
import com.videoai.monitoring.core.client.SpatialInfoTreeResponse;
import com.videoai.monitoring.core.dao.RegionDao;
import com.videoai.monitoring.core.entity.RegionEntity;
import com.videoai.monitoring.core.service.SpatialConfigService;
import com.videoai.monitoring.core.service.SpatialRegionSyncService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * 从空间服务 {@code /spatialServer/spatialInfo/tree} 同步区域树到设备管理页的区域管理。
 *
 * <p>硬约束：</p>
 * <ol>
 *   <li>只新增区域树中缺失的节点；已存在的同级同名节点一律复用，<b>不更新</b>名称、排序与父子关系；</li>
 *   <li>空间服务不可访问或返回失败时只记日志并返回 {@code success=false}，
 *       绝不抛异常，避免影响区域管理页面的其它操作。</li>
 * </ol>
 *
 * <p>空间服务基址来自界面配置（spatial_config），调用前通过 {@link SpatialBaseUrlHolder}
 * 覆盖 Feign 的目标地址。只同步园区/区域/楼栋/楼层（{@code children} 层级），
 * 不展开楼层下的房间（{@code roomInfoList}），因此查询固定带 {@code hasOther=true}。</p>
 */
@Slf4j
@Service
public class SpatialRegionSyncServiceImpl implements SpatialRegionSyncService {

    /** 空间服务 tree 接口的 hasOther 参数：true 才返回楼栋下的楼层子节点。 */
    private static final boolean INCLUDE_OTHER = true;

    private final SpatialInfoFeign spatialInfoFeign;
    private final SpatialConfigService spatialConfigService;
    private final RegionDao regionDao;

    public SpatialRegionSyncServiceImpl(SpatialInfoFeign spatialInfoFeign,
                                        SpatialConfigService spatialConfigService,
                                        RegionDao regionDao) {
        this.spatialInfoFeign = spatialInfoFeign;
        this.spatialConfigService = spatialConfigService;
        this.regionDao = regionDao;
    }

    @Override
    @Transactional
    public SpatialRegionSyncResponse sync() {
        String baseUrl = spatialConfigService.resolveBaseUrl();
        if (baseUrl == null) {
            log.warn("空间区域同步：未配置空间服务地址，跳过本次同步");
            return new SpatialRegionSyncResponse(false, "未配置空间服务地址，已跳过同步", 0, 0, 0);
        }

        SpatialInfoTreeResponse response;
        try {
            // 按界面配置覆盖 Feign 目标地址；先取远端数据（可能失败）再落库
            SpatialBaseUrlHolder.set(baseUrl);
            response = spatialInfoFeign.tree(INCLUDE_OTHER);
        } catch (Exception exception) {
            // 连接超时/拒绝、5xx、解析失败等：只记日志，不向页面报错
            log.warn("空间区域同步：空间服务 {} 不可访问，跳过本次同步：{}", baseUrl, exception.toString());
            return new SpatialRegionSyncResponse(false, "空间服务不可访问，已跳过同步", 0, 0, 0);
        } finally {
            SpatialBaseUrlHolder.clear();
        }

        if (response == null) {
            log.warn("空间区域同步：空间服务 {} 返回空响应，跳过本次同步", baseUrl);
            return new SpatialRegionSyncResponse(false, "空间服务返回空响应，已跳过同步", 0, 0, 0);
        }
        if (!response.status()) {
            log.warn("空间区域同步：空间服务 {} 返回失败 code={} message={}",
                    baseUrl, response.code(), response.message());
            return new SpatialRegionSyncResponse(false,
                    "空间服务返回失败：" + (isBlank(response.message()) ? "未知原因" : response.message()), 0, 0, 0);
        }

        List<SpatialInfoNode> roots = response.data() == null ? List.of() : response.data();
        Map<String, RegionEntity> bySibling = new HashMap<>();
        for (RegionEntity region : regionDao.selectAll()) {
            bySibling.put(siblingKey(region.getParentId(), region.getName()), region);
        }
        Counter counter = new Counter();
        for (SpatialInfoNode root : roots) {
            materialize(root, null, bySibling, counter);
        }
        log.info("空间区域同步完成（{}）：新增 {} 个，已存在跳过 {} 个", baseUrl, counter.created, counter.skipped);
        return new SpatialRegionSyncResponse(true, "同步完成", counter.created, counter.skipped,
                counter.created + counter.skipped);
    }

    /**
     * 递归补齐一个空间节点。同名同级节点已存在时复用它（不改动），否则新增；
     * 无论复用还是新增，子节点都挂到映射后的区域 id 下。
     */
    private void materialize(SpatialInfoNode node, UUID parentId, Map<String, RegionEntity> bySibling, Counter counter) {
        if (node == null) {
            return;
        }
        UUID mappedParentId = parentId;
        String name = clean(node.spatialName());
        if (name != null) {
            RegionEntity existing = bySibling.get(siblingKey(parentId, name));
            if (existing != null) {
                counter.skipped++;
                mappedParentId = existing.getId();
            } else {
                RegionEntity created = new RegionEntity();
                created.setId(UUID.randomUUID());
                created.setName(name);
                created.setParentId(parentId);
                // 追加到同级末尾：不移动、不重排已有区域
                created.setSortOrder(nextSortOrder(parentId));
                regionDao.insert(created);
                bySibling.put(siblingKey(parentId, name), created);
                counter.created++;
                mappedParentId = created.getId();
            }
        }
        if (node.children() != null) {
            for (SpatialInfoNode child : node.children()) {
                materialize(child, mappedParentId, bySibling, counter);
            }
        }
    }

    private int nextSortOrder(UUID parentId) {
        Integer max = regionDao.maxSortOrder(parentId);
        return max == null ? 0 : max + 1;
    }

    /** 同级判重键：父 id + 名称（父为空表示根节点）。 */
    private static String siblingKey(UUID parentId, String name) {
        return (parentId == null ? "" : parentId.toString()) + " " + name;
    }

    private static String clean(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }

    private static boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    private static final class Counter {
        private int created;
        private int skipped;
    }
}
