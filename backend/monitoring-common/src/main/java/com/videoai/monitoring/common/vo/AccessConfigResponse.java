package com.videoai.monitoring.common.vo;

import com.videoai.monitoring.common.dto.Ga1400Config;
import com.videoai.monitoring.common.dto.Gb28181Config;

public record AccessConfigResponse(
        Gb28181Config gb28181,
        Ga1400Config ga1400
) {
}
