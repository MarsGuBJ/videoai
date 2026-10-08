package com.videoai.monitoring.api;

import com.videoai.monitoring.common.dto.MatchRequest;
import com.videoai.monitoring.common.vo.MatchResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;

/**
 * Internal face-matching API contract (called by the worker). Implemented by a
 * controller in monitoring-core and proxied via Feign in monitoring-api-rpc.
 */
@Tag(name = "内部人脸比对")
@RequestMapping("/api/internal")
public interface InternalMatchApi {

    @PostMapping("/match")
    MatchResponse match(@Valid @RequestBody MatchRequest request);
}
