package com.videoai.monitoring.core.service.impl;

import com.videoai.monitoring.common.dto.RegionCreateRequest;
import com.videoai.monitoring.common.dto.RegionReorderRequest;
import com.videoai.monitoring.common.dto.RegionUpdateRequest;
import com.videoai.monitoring.common.vo.RegionNodeResponse;
import com.videoai.monitoring.core.dao.CameraDao;
import com.videoai.monitoring.core.dao.RegionDao;
import com.videoai.monitoring.core.entity.RegionEntity;
import com.videoai.monitoring.core.service.RegionService;
import com.videoai.monitoring.core.support.AreaPaths;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Deque;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
public class RegionServiceImpl implements RegionService {
    /** Camera area path segments are joined with " / " (space slash space). */
    private static final String PATH_SEPARATOR = " / ";

    private final RegionDao regionDao;
    private final CameraDao cameraDao;

    public RegionServiceImpl(RegionDao regionDao, CameraDao cameraDao) {
        this.regionDao = regionDao;
        this.cameraDao = cameraDao;
    }

    @Override
    @Transactional
    public List<RegionNodeResponse> tree() {
        List<RegionEntity> regions = new ArrayList<>(regionDao.selectAll());
        Map<String, RegionEntity> byParentAndName = new HashMap<>();
        for (RegionEntity region : regions) {
            byParentAndName.put(siblingKey(region.getParentId(), region.getName()), region);
        }
        // Sync: materialize region nodes implied by the free-text camera area paths.
        for (String area : cameraDao.selectDistinctAreas()) {
            UUID parentId = null;
            for (String segment : splitSegments(area)) {
                RegionEntity node = byParentAndName.get(siblingKey(parentId, segment));
                if (node == null) {
                    node = new RegionEntity();
                    node.setId(UUID.randomUUID());
                    node.setName(segment);
                    node.setParentId(parentId);
                    node.setSortOrder(nextSortOrder(parentId));
                    regionDao.insert(node);
                    regions.add(node);
                    byParentAndName.put(siblingKey(parentId, segment), node);
                }
                parentId = node.getId();
            }
        }
        Map<UUID, RegionEntity> byId = regions.stream()
                .collect(Collectors.toMap(RegionEntity::getId, Function.identity()));
        Map<String, Integer> counts = areaCounts();
        Map<UUID, List<RegionEntity>> childrenByParent = new HashMap<>();
        List<RegionEntity> roots = new ArrayList<>();
        for (RegionEntity region : regions) {
            if (region.getParentId() == null) {
                roots.add(region);
            } else {
                childrenByParent.computeIfAbsent(region.getParentId(), key -> new ArrayList<>()).add(region);
            }
        }
        roots.sort(regionOrder());
        childrenByParent.values().forEach(children -> children.sort(regionOrder()));
        List<RegionNodeResponse> tree = new ArrayList<>();
        for (RegionEntity root : roots) {
            tree.add(toNode(root, byId, childrenByParent, counts));
        }
        return tree;
    }

    @Override
    @Transactional
    public RegionNodeResponse create(RegionCreateRequest request) {
        String name = request.name().trim();
        UUID parentId = request.parentId();
        if (parentId != null && regionDao.selectById(parentId) == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "父区域不存在");
        }
        ensureUniqueSibling(parentId, name, null);
        RegionEntity entity = new RegionEntity();
        entity.setId(UUID.randomUUID());
        entity.setName(name);
        entity.setParentId(parentId);
        entity.setSortOrder(nextSortOrder(parentId));
        regionDao.insert(entity);
        return new RegionNodeResponse(entity.getId(), name, parentId, entity.getSortOrder(), 0, List.of());
    }

    @Override
    @Transactional
    public RegionNodeResponse rename(UUID id, RegionUpdateRequest request) {
        RegionEntity entity = requireEntity(id);
        String name = request.name().trim();
        ensureUniqueSibling(entity.getParentId(), name, id);
        String oldPath = fullPath(entity);
        entity.setName(name);
        regionDao.updateRegion(entity);
        String newPath = fullPath(entity);
        cameraDao.replaceAreaPrefix(oldPath, newPath);
        int deviceCount = areaCounts().getOrDefault(newPath, 0);
        return new RegionNodeResponse(entity.getId(), entity.getName(), entity.getParentId(),
                sortOrder(entity), deviceCount, List.of());
    }

    @Override
    @Transactional
    public void reorder(RegionReorderRequest request) {
        List<RegionEntity> children = regionDao.selectAll().stream()
                .filter(region -> Objects.equals(region.getParentId(), request.parentId()))
                .toList();
        Map<UUID, RegionEntity> byId = children.stream()
                .collect(Collectors.toMap(RegionEntity::getId, Function.identity()));
        List<UUID> orderedIds = request.orderedIds() != null ? request.orderedIds() : List.of();
        if (!byId.keySet().equals(new HashSet<>(orderedIds))) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "排序列表与现有子区域不一致");
        }
        for (int index = 0; index < orderedIds.size(); index++) {
            RegionEntity child = byId.get(orderedIds.get(index));
            child.setSortOrder(index);
            regionDao.updateRegion(child);
        }
    }

    @Override
    @Transactional
    public void delete(UUID id) {
        RegionEntity entity = requireEntity(id);
        boolean hasChildren = regionDao.selectAll().stream()
                .anyMatch(region -> id.equals(region.getParentId()));
        if (hasChildren) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "请先删除子区域");
        }
        int devices = cameraDao.countByAreaPrefix(fullPath(entity));
        if (devices > 0) {
            throw new ResponseStatusException(HttpStatus.CONFLICT,
                    "该区域下存在 " + devices + " 台设备，无法删除");
        }
        regionDao.deleteById(id);
    }

    private RegionNodeResponse toNode(RegionEntity entity, Map<UUID, RegionEntity> byId,
                                      Map<UUID, List<RegionEntity>> childrenByParent,
                                      Map<String, Integer> counts) {
        List<RegionNodeResponse> children = new ArrayList<>();
        for (RegionEntity child : childrenByParent.getOrDefault(entity.getId(), List.of())) {
            children.add(toNode(child, byId, childrenByParent, counts));
        }
        int deviceCount = counts.getOrDefault(fullPath(entity, byId), 0);
        return new RegionNodeResponse(entity.getId(), entity.getName(), entity.getParentId(),
                sortOrder(entity), deviceCount, children);
    }

    private RegionEntity requireEntity(UUID id) {
        RegionEntity entity = regionDao.selectById(id);
        if (entity == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "区域不存在");
        }
        return entity;
    }

    /** 同级区域名称唯一（不加 DB 唯一约束，与云平台等模块保持一致）。 */
    private void ensureUniqueSibling(UUID parentId, String name, UUID excludeId) {
        boolean taken = regionDao.selectByParentAndName(parentId, name).stream()
                .anyMatch(existing -> excludeId == null || !excludeId.equals(existing.getId()));
        if (taken) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "同级区域名称已存在");
        }
    }

    private int nextSortOrder(UUID parentId) {
        Integer max = regionDao.maxSortOrder(parentId);
        return max == null ? 0 : max + 1;
    }

    /** Full path ("父 / 子 / 孙") by walking the parent chain via the DAO. */
    private String fullPath(RegionEntity entity) {
        Deque<String> names = new ArrayDeque<>();
        RegionEntity current = entity;
        while (current != null) {
            names.addFirst(current.getName());
            current = current.getParentId() != null ? regionDao.selectById(current.getParentId()) : null;
        }
        return String.join(PATH_SEPARATOR, names);
    }

    /** Full path using an in-memory id index (tree building already loaded all rows). */
    private String fullPath(RegionEntity entity, Map<UUID, RegionEntity> byId) {
        Deque<String> names = new ArrayDeque<>();
        RegionEntity current = entity;
        while (current != null) {
            names.addFirst(current.getName());
            current = current.getParentId() != null ? byId.get(current.getParentId()) : null;
        }
        return String.join(PATH_SEPARATOR, names);
    }

    private Map<String, Integer> areaCounts() {
        Map<String, Integer> counts = new HashMap<>();
        for (Map<String, Object> row : cameraDao.selectAreaCounts()) {
            Object area = row.get("area");
            Object cnt = row.get("cnt");
            if (area != null && cnt instanceof Number number) {
                // 历史数据分隔符可能不带空格（东区/一车间），按规范化路径归并计数
                String normalized = AreaPaths.normalize(area.toString());
                if (normalized != null) {
                    counts.merge(normalized, number.intValue(), Integer::sum);
                }
            }
        }
        return counts;
    }

    /** Split a camera area path on "/", trim each segment, drop empties. */
    static List<String> splitSegments(String area) {
        List<String> segments = new ArrayList<>();
        for (String segment : area.split("/")) {
            String trimmed = segment.trim();
            if (!trimmed.isEmpty()) {
                segments.add(trimmed);
            }
        }
        return segments;
    }

    private static String siblingKey(UUID parentId, String name) {
        return (parentId == null ? "" : parentId.toString()) + " " + name;
    }

    private static int sortOrder(RegionEntity entity) {
        return entity.getSortOrder() == null ? 0 : entity.getSortOrder();
    }

    private static Comparator<RegionEntity> regionOrder() {
        return Comparator.comparing(RegionEntity::getSortOrder, Comparator.nullsFirst(Comparator.naturalOrder()))
                .thenComparing(RegionEntity::getCreatedAt, Comparator.nullsLast(Comparator.naturalOrder()));
    }
}
