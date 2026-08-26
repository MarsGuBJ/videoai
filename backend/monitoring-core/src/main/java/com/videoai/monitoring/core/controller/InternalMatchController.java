package com.videoai.monitoring.core.controller;

import com.videoai.monitoring.api.InternalMatchApi;
import com.videoai.monitoring.common.dto.MatchRequest;
import com.videoai.monitoring.common.vo.MatchCandidate;
import com.videoai.monitoring.common.vo.MatchResponse;
import com.videoai.monitoring.core.config.VideoAiProperties;
import com.videoai.monitoring.core.service.FaceProfileService;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class InternalMatchController implements InternalMatchApi {
    private final FaceProfileService faceProfileService;
    private final VideoAiProperties properties;

    public InternalMatchController(FaceProfileService faceProfileService, VideoAiProperties properties) {
        this.faceProfileService = faceProfileService;
        this.properties = properties;
    }

    @Override
    public MatchResponse match(MatchRequest request) {
        double threshold = request.threshold() == null ? properties.matching().threshold() : request.threshold();
        MatchCandidate candidate = faceProfileService.match(request.embedding(), threshold);
        if (candidate == null) {
            return new MatchResponse(false, null, null, null, null, 0.0);
        }
        return new MatchResponse(
                true,
                candidate.id(),
                candidate.name(),
                candidate.description(),
                candidate.photoPath(),
                candidate.similarity()
        );
    }
}
