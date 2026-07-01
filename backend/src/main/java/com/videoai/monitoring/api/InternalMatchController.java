package com.videoai.monitoring.api;

import com.videoai.monitoring.config.VideoAiProperties;
import com.videoai.monitoring.dto.FaceDtos.MatchCandidate;
import com.videoai.monitoring.dto.MatchDtos.MatchRequest;
import com.videoai.monitoring.dto.MatchDtos.MatchResponse;
import com.videoai.monitoring.service.FaceProfileService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/internal")
public class InternalMatchController {
    private final FaceProfileService faceProfileService;
    private final VideoAiProperties properties;

    public InternalMatchController(FaceProfileService faceProfileService, VideoAiProperties properties) {
        this.faceProfileService = faceProfileService;
        this.properties = properties;
    }

    @PostMapping("/match")
    MatchResponse match(@Valid @RequestBody MatchRequest request) {
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

