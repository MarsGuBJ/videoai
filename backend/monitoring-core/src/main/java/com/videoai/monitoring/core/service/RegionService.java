package com.videoai.monitoring.core.service;

import com.videoai.monitoring.common.dto.RegionCreateRequest;
import com.videoai.monitoring.common.dto.RegionReorderRequest;
import com.videoai.monitoring.common.dto.RegionUpdateRequest;
import com.videoai.monitoring.common.vo.RegionNodeResponse;

import java.util.List;
import java.util.UUID;

/**
 * Region tree CRUD. The tree stays in sync with the free-text camera area paths:
 * reading the tree first materializes any missing nodes implied by camera areas,
 * and renaming a node rewrites the matching area prefix on cameras.
 */
public interface RegionService {

    /** Full nested tree (syncing camera area paths into region nodes first). */
    List<RegionNodeResponse> tree();

    RegionNodeResponse create(RegionCreateRequest request);

    RegionNodeResponse rename(UUID id, RegionUpdateRequest request);

    void reorder(RegionReorderRequest request);

    void delete(UUID id);
}
