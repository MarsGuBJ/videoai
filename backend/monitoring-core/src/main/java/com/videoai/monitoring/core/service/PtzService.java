package com.videoai.monitoring.core.service;

import com.videoai.monitoring.common.dto.PtzControlRequest;
import com.videoai.monitoring.common.vo.PtzControlResponse;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.util.Map;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Hikvision ISAPI PTZ control ported from backend-lite/main.py
 * (resolve_hikvision_ptz_target, dispatch_hikvision_ptz, hikvision_xml_request).
 */
public interface PtzService {

    Pattern TRACK_ID_PATTERN = Pattern.compile("/Streaming/Channels/(\\d+)", Pattern.CASE_INSENSITIVE);

    PtzControlResponse control(UUID cameraId, PtzControlRequest request);

    record PtzTarget(String baseUrl, String channel, String username, String password) {
    }

    /** Planned ISAPI request, exposed for testing. */
    record PtzPlan(String method, String path, String body) {
    }

    static PtzPlan plan(String command, Integer step, Integer preset, String channel) {
        String normalized = command.strip().toLowerCase();
        switch (normalized) {
            case "up", "down", "left", "right", "up_left", "up_right", "down_left", "down_right",
                 "zoom_in", "zoom_out", "stop" -> {
                int[] vector = ptzVector(normalized, step);
                String body = "<PTZData><pan>" + vector[0] + "</pan><tilt>" + vector[1]
                        + "</tilt><zoom>" + vector[2] + "</zoom></PTZData>";
                return new PtzPlan("PUT", "/ISAPI/PTZCtrl/channels/" + channel + "/continuous", body);
            }
            case "home" -> {
                return new PtzPlan("PUT", "/ISAPI/PTZCtrl/channels/" + channel + "/homeposition/goto", "");
            }
            case "preset_goto" -> {
                int presetValue = preset != null ? preset : 0;
                if (presetValue < 1 || presetValue > 255) {
                    throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Preset must be between 1 and 255");
                }
                return new PtzPlan("PUT",
                        "/ISAPI/PTZCtrl/channels/" + channel + "/presets/" + presetValue + "/goto", "");
            }
            default -> throw new ResponseStatusException(HttpStatus.BAD_REQUEST,
                    "Unsupported PTZ command: " + command);
        }
    }

    static int[] ptzVector(String command, Integer rawStep) {
        int step = Math.max(1, Math.min(10, rawStep != null ? rawStep : 1)) * 10;
        Map<String, int[]> vectors = Map.ofEntries(
                Map.entry("up", new int[]{0, step, 0}),
                Map.entry("down", new int[]{0, -step, 0}),
                Map.entry("left", new int[]{-step, 0, 0}),
                Map.entry("right", new int[]{step, 0, 0}),
                Map.entry("up_left", new int[]{-step, step, 0}),
                Map.entry("up_right", new int[]{step, step, 0}),
                Map.entry("down_left", new int[]{-step, -step, 0}),
                Map.entry("down_right", new int[]{step, -step, 0}),
                Map.entry("zoom_in", new int[]{0, 0, step}),
                Map.entry("zoom_out", new int[]{0, 0, -step}),
                Map.entry("stop", new int[]{0, 0, 0}));
        return vectors.get(command);
    }

    static String parseTrackId(String path) {
        if (path == null) {
            return null;
        }
        Matcher matcher = TRACK_ID_PATTERN.matcher(path);
        return matcher.find() ? matcher.group(1) : null;
    }

    static String normalizeChannel(String track) {
        if (track == null) {
            return null;
        }
        String value = track.strip();
        if (value.matches("\\d+") && value.length() >= 3 && (value.endsWith("01") || value.endsWith("02"))) {
            value = String.valueOf(Integer.parseInt(value.substring(0, value.length() - 2)));
        }
        return value.isEmpty() ? null : value;
    }
}
