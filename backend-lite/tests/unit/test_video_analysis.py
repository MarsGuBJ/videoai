"""MinIO 视频智能分析代理的单元测试。"""

import pytest
import requests
from fastapi.testclient import TestClient

from app.services import video_analysis


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self.payload


def test_analyze_proxy_maps_payload_and_forwards_response(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """camelCase 入参映射为 snake_case，上游 2xx 响应原样透传。"""
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse({"code": 0, "data": {"result": "有人出现"}})

    monkeypatch.setattr(requests, "post", fake_post)

    response = client.post(
        "/api/video-analysis/analyze",
        json={"videoUrl": " http://192.168.11.194:9000/public/a.mp4 ", "prompt": "是否有人出现"},
    )

    assert response.status_code == 200
    assert response.json() == {"code": 0, "data": {"result": "有人出现"}}
    assert captured["url"] == "http://192.168.11.192:8775/analyze_minio_video"
    assert captured["json"] == {
        "video_url": "http://192.168.11.194:9000/public/a.mp4",
        "fps": 1,
        "segment_seconds": 60,
        "max_segments": 1,
        "height": 480,
        "prompt": "是否有人出现",
    }
    assert captured["timeout"] == video_analysis.VIDEO_ANALYSIS_API_TIMEOUT_SECONDS


def test_analyze_proxy_clamps_numeric_fields(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """数值字段小于 1 时按 1 处理。"""
    captured = {}

    def fake_post(url, json, timeout):
        captured["json"] = json
        return FakeResponse({"code": 0})

    monkeypatch.setattr(requests, "post", fake_post)

    response = client.post(
        "/api/video-analysis/analyze",
        json={
            "videoUrl": "http://192.168.11.194:9000/public/a.mp4",
            "prompt": "分析",
            "fps": 0,
            "segmentSeconds": 0,
            "maxSegments": 0,
            "height": 0,
        },
    )

    assert response.status_code == 200
    assert captured["json"]["fps"] == 1
    assert captured["json"]["segment_seconds"] == 1
    assert captured["json"]["max_segments"] == 1
    assert captured["json"]["height"] == 1


@pytest.mark.parametrize(
    "payload",
    [
        {"videoUrl": "", "prompt": "分析"},
        {"videoUrl": "http://192.168.11.194:9000/public/a.mp4", "prompt": "  "},
    ],
)
def test_analyze_proxy_rejects_blank_required_fields(client: TestClient, payload):
    """videoUrl / prompt 为空白时返回 400。"""
    response = client.post("/api/video-analysis/analyze", json=payload)
    assert response.status_code == 400


def test_analyze_proxy_passes_through_upstream_error(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """上游非 2xx 时按原状态码透传。"""

    def fake_post(url, json, timeout):
        return FakeResponse({"message": "boom"}, status_code=500)

    monkeypatch.setattr(requests, "post", fake_post)

    response = client.post(
        "/api/video-analysis/analyze",
        json={"videoUrl": "http://192.168.11.194:9000/public/a.mp4", "prompt": "分析"},
    )

    assert response.status_code == 500


def test_analyze_proxy_upstream_unavailable(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """上游不可达时返回 502。"""

    def fake_post(url, json, timeout):
        raise requests.ConnectionError("refused")

    monkeypatch.setattr(requests, "post", fake_post)

    response = client.post(
        "/api/video-analysis/analyze",
        json={"videoUrl": "http://192.168.11.194:9000/public/a.mp4", "prompt": "分析"},
    )

    assert response.status_code == 502


class FakeCamera:
    def __init__(self, nvr_track_id):
        self.nvrTrackId = nvr_track_id


def test_recording_file_proxy_happy_path(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """按摄像头 nvrTrackId 调 MCP 导出接口并透传 data。"""
    from app.services import camera_cache

    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse({"data": {"videoUrl": "http://192.168.11.194:9000/public/recordings/exports/201/a.mp4"}})

    monkeypatch.setattr(camera_cache, "get", lambda camera_id: FakeCamera("201"))
    monkeypatch.setattr(requests, "post", fake_post)

    response = client.post(
        "/api/video-analysis/recording-file",
        json={"cameraId": "cam-1", "startTime": "2026-08-31 10:00", "endTime": "2026-08-31 10:02"},
    )

    assert response.status_code == 200
    assert response.json()["videoUrl"].endswith("a.mp4")
    assert captured["url"] == "http://192.168.11.194:8097/export_recording-http"
    assert captured["json"] == {
        "cameraId": "cam-1",
        "trackId": "201",
        "startTime": "2026-08-31 10:00",
        "endTime": "2026-08-31 10:02",
    }
    assert captured["timeout"] == video_analysis.MCP_EXPORT_TIMEOUT_SECONDS


def test_recording_file_proxy_camera_not_found(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """摄像头不在缓存中时返回 404。"""
    from app.services import camera_cache

    monkeypatch.setattr(camera_cache, "get", lambda camera_id: None)

    response = client.post(
        "/api/video-analysis/recording-file",
        json={"cameraId": "cam-x", "startTime": "2026-08-31 10:00", "endTime": "2026-08-31 10:02"},
    )

    assert response.status_code == 404


def test_recording_file_proxy_unbound_camera_still_proxied(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """摄像头未绑定 NVR track 时不再本地 400：透传 MCP（trackId 置空，由 MCP 反查所属 NVR）。"""
    from app.services import camera_cache

    captured = {}

    def fake_post(url, json, timeout):
        captured["json"] = json
        return FakeResponse({"data": {"videoUrl": "http://192.168.11.194:9000/public/recordings/exports/201/a.mp4"}})

    monkeypatch.setattr(camera_cache, "get", lambda camera_id: FakeCamera(None))
    monkeypatch.setattr(requests, "post", fake_post)

    response = client.post(
        "/api/video-analysis/recording-file",
        json={"cameraId": "cam-1", "startTime": "2026-08-31 10:00", "endTime": "2026-08-31 10:02"},
    )

    assert response.status_code == 200
    assert captured["json"]["trackId"] == ""


def test_recording_file_proxy_mcp_unavailable(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """MCP 不可达时返回 502。"""
    from app.services import camera_cache

    def fake_post(url, json, timeout):
        raise requests.ConnectionError("refused")

    monkeypatch.setattr(camera_cache, "get", lambda camera_id: FakeCamera("201"))
    monkeypatch.setattr(requests, "post", fake_post)

    response = client.post(
        "/api/video-analysis/recording-file",
        json={"cameraId": "cam-1", "startTime": "2026-08-31 10:00", "endTime": "2026-08-31 10:02"},
    )

    assert response.status_code == 502


class FakeMinio:
    def __init__(self):
        self.uploads = []

    def bucket_exists(self, bucket):
        return True

    def fput_object(self, bucket, object_name, file_path, content_type=None):
        self.uploads.append((bucket, object_name, content_type))


def test_upload_video_returns_minio_url(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """上传本地视频到 MinIO，返回可拉取的 videoUrl。"""
    from app.services import video_storage

    fake = FakeMinio()
    monkeypatch.setattr(video_storage, "_get_minio_client", lambda: fake)
    video_storage._reset_minio_client_for_test()

    response = client.post(
        "/api/video-analysis/upload-video",
        files={"file": ("demo.mp4", b"fake-mp4-bytes", "video/mp4")},
    )

    assert response.status_code == 200
    url = response.json()["videoUrl"]
    assert url.startswith("http://192.168.11.194:9000/public/recordings/uploads/")
    assert url.endswith(".mp4")
    assert fake.uploads[0][2] == "video/mp4"


def test_upload_video_rejects_non_video_suffix(client: TestClient):
    """不支持的后缀返回 400。"""
    response = client.post(
        "/api/video-analysis/upload-video",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 400


def test_upload_video_rejects_empty_file(client: TestClient):
    """空文件返回 400。"""
    response = client.post(
        "/api/video-analysis/upload-video",
        files={"file": ("empty.mp4", b"", "video/mp4")},
    )

    assert response.status_code == 400


class FakeProcess:
    def __init__(self, stdout=b"jpeg-bytes", returncode=0):
        self.stdout = stdout
        self.returncode = returncode


def test_frame_endpoint_extracts_jpeg(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """按 videoUrl + seconds 调 ffmpeg 截帧并返回 JPEG。"""
    captured = {}

    def fake_run(args, capture_output, timeout):
        captured["args"] = args
        captured["timeout"] = timeout
        return FakeProcess()

    monkeypatch.setattr(video_analysis.subprocess, "run", fake_run)

    response = client.get(
        "/api/video-analysis/frame",
        params={"videoUrl": "http://192.168.11.194:9000/public/a.mp4", "seconds": 65},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == b"jpeg-bytes"
    args = captured["args"]
    assert args[args.index("-ss") + 1] == "65.000"
    assert args[args.index("-i") + 1] == "http://192.168.11.194:9000/public/a.mp4"
    assert captured["timeout"] == video_analysis.VIDEO_FRAME_TIMEOUT_SECONDS


def test_frame_endpoint_rejects_non_http_url(client: TestClient):
    """非 http(s) 地址返回 400。"""
    response = client.get(
        "/api/video-analysis/frame",
        params={"videoUrl": "file:///etc/passwd", "seconds": 0},
    )

    assert response.status_code == 400


def test_frame_endpoint_502_when_ffmpeg_fails(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """ffmpeg 失败或无输出时返回 502。"""
    monkeypatch.setattr(
        video_analysis.subprocess, "run", lambda *a, **kw: FakeProcess(stdout=b"", returncode=1)
    )

    response = client.get(
        "/api/video-analysis/frame",
        params={"videoUrl": "http://192.168.11.194:9000/public/a.mp4", "seconds": 0},
    )

    assert response.status_code == 502
