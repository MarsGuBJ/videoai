package com.videoai.monitoring.core.service.impl;

import com.videoai.monitoring.common.dto.PtzControlRequest;
import com.videoai.monitoring.common.vo.CameraResponse;
import com.videoai.monitoring.common.vo.PtzControlResponse;
import com.videoai.monitoring.core.client.DigestHttpClient;
import com.videoai.monitoring.core.config.VideoAiProperties;
import com.videoai.monitoring.core.service.CameraService;
import com.videoai.monitoring.core.service.PtzService;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.net.URI;
import java.net.URLDecoder;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.UUID;

@Service
public class PtzServiceImpl implements PtzService {
    private static final Duration PTZ_TIMEOUT = Duration.ofSeconds(5);

    private final CameraService cameraService;
    private final VideoAiProperties properties;
    private final DigestHttpClient digestHttpClient;

    public PtzServiceImpl(CameraService cameraService, VideoAiProperties properties, DigestHttpClient digestHttpClient) {
        this.cameraService = cameraService;
        this.properties = properties;
        this.digestHttpClient = digestHttpClient;
    }

    @Override
    public PtzControlResponse control(UUID cameraId, PtzControlRequest request) {
        CameraResponse camera = cameraService.get(cameraId);
        PtzTarget target = resolveTarget(camera);
        dispatch(target, request);
        return new PtzControlResponse(
                camera.id(),
                request.command(),
                target.channel(),
                URI.create(target.baseUrl()).getAuthority(),
                true);
    }

    // --- target resolution (resolve_hikvision_ptz_target) ---

    PtzTarget resolveTarget(CameraResponse camera) {
        URI parsedSource = parseUri(camera.sourceUrl());
        String[] baseResolution = resolveBaseUrl(camera, parsedSource);
        String baseUrl = baseResolution[0];
        boolean baseFromSource = Boolean.parseBoolean(baseResolution[1]);
        if (baseUrl == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Cannot resolve Hikvision NVR base URL");
        }

        String channel = resolveChannel(camera, parsedSource, baseFromSource);
        if (channel == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST,
                    "Cannot resolve PTZ channel from camera NVR fields or RTSP URL");
        }

        String username = userInfoPart(parsedSource, 0);
        if (username == null || username.isEmpty()) {
            username = properties.hikvision().nvrUsername();
        }
        String password = userInfoPart(parsedSource, 1);
        if (password == null || password.isEmpty()) {
            password = properties.hikvision().nvrPassword();
        }
        if (username == null || username.isEmpty() || password == null || password.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Hikvision PTZ credentials are not configured");
        }

        return new PtzTarget(stripTrailingSlash(baseUrl), channel, username, password);
    }

    private String[] resolveBaseUrl(CameraResponse camera, URI parsedSource) {
        String nvrId = clean(camera.nvrId());
        if (nvrId != null) {
            if (nvrId.startsWith("http://") || nvrId.startsWith("https://")) {
                return new String[]{stripTrailingSlash(nvrId), "false"};
            }
            if (nvrId.contains(".") || nvrId.contains(":")) {
                return new String[]{stripTrailingSlash("http://" + nvrId), "false"};
            }
        }
        String scheme = parsedSource.getScheme();
        if (("http".equals(scheme) || "https".equals(scheme)) && parsedSource.getAuthority() != null) {
            return new String[]{stripTrailingSlash(scheme + "://" + parsedSource.getAuthority()), "true"};
        }
        if ("rtsp".equals(scheme) && parsedSource.getHost() != null) {
            return new String[]{stripTrailingSlash("http://" + parsedSource.getHost()), "true"};
        }
        String configured = properties.hikvision().nvrBaseUrl();
        if (configured != null && !configured.isBlank()) {
            return new String[]{configured, "false"};
        }
        return new String[]{null, "false"};
    }

    private String resolveChannel(CameraResponse camera, URI parsedSource, boolean baseFromSource) {
        String sourceTrack = PtzService.parseTrackId(parsedSource.getPath());
        if (baseFromSource && sourceTrack != null) {
            return PtzService.normalizeChannel(sourceTrack);
        }
        String channelSource = clean(camera.nvrChannel());
        if (channelSource != null) {
            return channelSource;
        }
        String track = clean(camera.nvrTrackId());
        if (track == null) {
            track = sourceTrack;
        }
        return PtzService.normalizeChannel(track);
    }

    // --- dispatch (dispatch_hikvision_ptz / ptz_vector) ---

    private void dispatch(PtzTarget target, PtzControlRequest request) {
        PtzPlan planned = PtzService.plan(request.command(), request.step(), request.preset(), target.channel());
        xmlRequest(target, planned.method(), planned.path(), planned.body());
    }

    // --- transport (hikvision_xml_request: digest first, then basic) ---

    private void xmlRequest(PtzTarget target, String method, String path, String body) {
        String url = target.baseUrl() + path;
        String lastDetail = "";

        try {
            HttpResponse<byte[]> response = digestHttpClient.sendWithDigest(
                    method, url, target.username(), target.password(), body, PTZ_TIMEOUT);
            if (response.statusCode() >= 200 && response.statusCode() < 300) {
                return;
            }
            lastDetail = detail(response);
            if (response.statusCode() != 401) {
                throw new ResponseStatusException(HttpStatus.BAD_GATEWAY,
                        "Hikvision PTZ request failed (" + response.statusCode() + "): " + lastDetail);
            }
        } catch (IOException exception) {
            lastDetail = exception.getMessage();
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            lastDetail = "interrupted";
        }

        try {
            HttpResponse<byte[]> response = digestHttpClient.sendWithBasic(
                    method, url, target.username(), target.password(), body, PTZ_TIMEOUT);
            if (response.statusCode() >= 200 && response.statusCode() < 300) {
                return;
            }
            lastDetail = detail(response);
        } catch (IOException exception) {
            lastDetail = exception.getMessage();
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            lastDetail = "interrupted";
        }
        throw new ResponseStatusException(HttpStatus.BAD_GATEWAY,
                "Hikvision PTZ request failed: " + (lastDetail.isEmpty() ? "authentication failed" : lastDetail));
    }

    private static String detail(HttpResponse<byte[]> response) {
        String text = new String(response.body(), StandardCharsets.UTF_8).strip();
        return text.isEmpty() ? String.valueOf(response.statusCode()) : text;
    }

    private static URI parseUri(String sourceUrl) {
        try {
            return URI.create(sourceUrl);
        } catch (IllegalArgumentException exception) {
            return URI.create("http://invalid");
        }
    }

    private static String userInfoPart(URI uri, int index) {
        String userInfo = uri.getUserInfo();
        if (userInfo == null) {
            return null;
        }
        String[] parts = userInfo.split(":", 2);
        if (index >= parts.length) {
            return null;
        }
        return URLDecoder.decode(parts[index], StandardCharsets.UTF_8);
    }

    private static String clean(String value) {
        if (value == null) {
            return null;
        }
        String cleaned = value.strip();
        return cleaned.isEmpty() ? null : cleaned;
    }

    private static String stripTrailingSlash(String value) {
        String result = value;
        while (result.endsWith("/")) {
            result = result.substring(0, result.length() - 1);
        }
        return result;
    }
}
