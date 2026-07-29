from datetime import datetime, timezone
import asyncio

import httpx

import app.server as server
from app.models import Camera, RecordingSegment


def post(path: str, json: dict) -> httpx.Response:
    async def run_request():
        transport = httpx.ASGITransport(app=server.mcp.streamable_http_app())
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(path, json=json)

    return asyncio.run(run_request())


def make_camera(**overrides) -> Camera:
    now = datetime(2026, 7, 8, tzinfo=timezone.utc)
    data = {
        "id": "cam-1",
        "name": "园区摄像头",
        "sourceUrl": "rtsp://camera/live",
        "streamApp": "live",
        "streamName": "cam-1",
        "status": "RUNNING",
        "playbackUrl": "/live/cam-1.live.flv",
        "createdAt": now,
        "updatedAt": now,
        "nvrId": "main-nvr",
        "nvrChannel": "101",
        "nvrTrackId": "101",
        "nvrStreamType": "main",
    }
    data.update(overrides)
    return Camera(**data)


def test_list_cameras_http_returns_json(monkeypatch):
    async def fake_list_cameras():
        return [make_camera()]

    monkeypatch.setattr(server.videoai, "list_cameras", fake_list_cameras)
    monkeypatch.setattr(server, "_public_url", lambda url: f"http://video.example{url}")

    response = post("/list_cameras-http", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"][0]["cameraId"] == "cam-1"
    assert payload["data"][0]["url"] == "http://video.example/live/cam-1.live.flv"
    assert payload["xml"].startswith("<?xml")


def test_search_recordings_http_uses_beijing_time_and_boolean_conversion(monkeypatch):
    calls = []

    def fake_build_recording(start_time, end_time):
        calls.append((start_time, end_time))
        return RecordingSegment(
            recordingId="rec-hcn",
            cameraId="cam-hcn",
            cameraName="IPC-198",
            trackId="1",
            startTime=start_time,
            endTime=end_time,
            playbackUri="hcnetsdk://192.168.11.198:8000/channels/1",
            source="hikvision_hcnetsdk_playback",
        )

    monkeypatch.setattr(server.hcnetsdk_playback, "build_recording", fake_build_recording)

    response = post(
        "/search_recordings-http",
        json={
            "startTime": "2026-07-08T00:00:00",
            "endTime": "2026-07-08T00:05:00",
            "trackId": "601",
            "autoProxy": "false",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"][0]["startTime"] == "2026-07-08T00:00:00+08:00"
    assert payload["data"][0].get("url") is None
    assert "streamUrl" not in payload["data"][0]
    assert calls[0][0].utcoffset().total_seconds() == 8 * 60 * 60
    assert calls[0][0].hour == 0


def test_get_recording_stream_is_not_registered_as_mcp_tool():
    tool_names = {tool.name for tool in asyncio.run(server.mcp.list_tools())}

    assert "get_recording_stream" not in tool_names


def test_get_recording_stream_http_route_remains_available(monkeypatch):
    start = datetime(2026, 7, 8, tzinfo=timezone.utc)
    recording = RecordingSegment(
        recordingId="rec-http-compat",
        cameraId="cam-hcn",
        cameraName="IPC-198",
        trackId="1",
        startTime=start,
        endTime=start.replace(minute=5),
        playbackUri="hcnetsdk://192.168.11.198:8000/channels/1",
        source=server.NET_DVR_PLAYBACK_BY_TIME,
    )

    async def fake_start_playback(cached_recording):
        assert cached_recording.recordingId == recording.recordingId
        return "http://zlm/live/rec-http-compat.live.flv"

    server.recording_cache.put_many([recording])
    monkeypatch.setattr(server.hcnetsdk_playback, "start_playback", fake_start_playback)

    response = post(
        "/get_recording_stream-http",
        json={"recordingId": recording.recordingId, "format": "flv"},
    )

    assert response.status_code == 200
    assert response.json()["format"] == "flv"
    assert response.json()["url"] == "http://zlm/live/rec-http-compat.live.flv"


def test_download_recording_http_route(monkeypatch, tmp_path):
    temp_mp4 = tmp_path / "download.mp4"
    temp_mp4.write_bytes(b"mp4")

    class FakeDownloader:
        channel = 1

        def build_download_recording(self, start_time, end_time):
            from app.hcnetsdk_playback import build_hcnetsdk_download_recording

            return build_hcnetsdk_download_recording("10.10.7.252", 8000, self.channel, start_time, end_time)

        async def download_mp4(self, recording):
            return temp_mp4

    def fake_upload_mp4(source_file, object_name):
        return f"http://minio/public/{object_name}"

    monkeypatch.setattr(server, "hcnetsdk_downloaders", {"10.10.7.252": FakeDownloader()}, raising=False)
    monkeypatch.setattr(server.recording_mp4_storage, "upload_mp4", fake_upload_mp4)

    response = post(
        "/download_recording-http",
        json={
            "nvr": "10.10.7.252",
            "startTime": "2026-07-08T00:00:00",
            "endTime": "2026-07-08T00:05:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"][0]["format"] == "mp4"
    assert payload["data"][0]["url"].startswith("http://minio/public/recordings/")
    assert payload["data"][0]["metadata"]["deviceHost"] == "10.10.7.252"


def test_download_recording_http_requires_nvr():
    response = post(
        "/download_recording-http",
        json={
            "startTime": "2026-07-08T00:00:00",
            "endTime": "2026-07-08T00:05:00",
        },
    )

    assert response.status_code == 400
    assert "nvr" in response.json()["error"]["message"]


def test_download_recording_http_rejects_unknown_nvr():
    response = post(
        "/download_recording-http",
        json={
            "nvr": "10.10.7.254",
            "startTime": "2026-07-08T00:00:00",
            "endTime": "2026-07-08T00:05:00",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "nvr must be one of: 10.10.7.252, 10.10.7.253"


def test_download_recording_mcp_schema_requires_nvr():
    tools = asyncio.run(server.mcp.list_tools())
    download_tool = next(tool for tool in tools if tool.name == "download_recording")

    assert "nvr" in download_tool.inputSchema["required"]


def test_upload_face_image_http_uses_image_url(monkeypatch):
    calls = []

    async def fake_upload_face(image_url, camera_id, model_name, name):
        calls.append((image_url, camera_id, model_name, name))
        return {"faceId": "face-1"}

    async def fake_get_face(face_id):
        calls.append(("get_face", face_id))
        return {"id": "face-1", "name": "张三", "photoUrl": "/api/assets/faces/face-1.jpg"}

    async def fake_create_deployment_task(payload):
        calls.append(("create_deployment_task", payload))
        return {
            "id": "task-1",
            "name": payload["name"],
            "enabled": payload["enabled"],
            "taskStatus": "running",
            "faceProfileId": payload["faceProfileId"],
            "cameraIds": payload["cameraIds"],
        }

    monkeypatch.setattr(server.videoai, "upload_face", fake_upload_face)
    monkeypatch.setattr(server.videoai, "get_face", fake_get_face)
    monkeypatch.setattr(server.videoai, "create_deployment_task", fake_create_deployment_task)

    response = post(
        "/upload_face_image-http",
        json={
            "imageUrl": "http://example.test/face.jpg",
            "cameraId": "cam-1",
            "modelName": "retinaface_mobilenet",
            "name": "张三",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["faceId"] == "face-1"
    assert payload["deploymentTaskId"] == "task-1"
    assert payload["deploymentTask"]["enabled"] is True
    assert payload["deploymentTask"]["taskStatus"] == "running"
    assert calls[0] == ("http://example.test/face.jpg", "cam-1", "retinaface_mobilenet", "张三")
    assert calls[1] == ("get_face", "face-1")
    assert calls[2][0] == "create_deployment_task"
    assert calls[2][1]["cameraIds"] == ["cam-1"]
    assert calls[2][1]["faceProfileId"] == "face-1"
    assert calls[2][1]["faceProfilePhotoUrl"] == "/api/assets/faces/face-1.jpg"


def test_dino_events_http_converts_limit_to_integer(monkeypatch):
    async def fake_list_cameras():
        return []

    async def fake_list_deployment_tasks():
        return []

    monkeypatch.setattr(server.videoai, "list_cameras", fake_list_cameras)
    monkeypatch.setattr(server.videoai, "list_deployment_tasks", fake_list_deployment_tasks)

    response = post("/dino_events-http", json={"limit": "2"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert len(payload["data"]) == 2


def test_detect_persons_http_route(monkeypatch):
    async def fake_detect_persons(image_url):
        return {"code": 200, "data": {"image_url": image_url}}

    monkeypatch.setattr(server.person_api, "detect_persons", fake_detect_persons)

    response = post("/detect_persons-http", json={"imageUrl": "http://example.test/query.jpg"})

    assert response.status_code == 200
    assert response.json()["data"]["image_url"] == "http://example.test/query.jpg"


def test_search_person_by_bbox_http_converts_numeric_arguments(monkeypatch):
    calls = []
    bbox = [{"x": 1, "y": 2}, {"x": 3, "y": 2}, {"x": 3, "y": 4}, {"x": 1, "y": 4}]

    async def fake_search_person_by_bbox(
        image_url,
        bbox=None,
        search_method="reid",
        start_time="",
        end_time="",
        similarity_threshold=0.6,
        top_k=10,
    ):
        calls.append((image_url, bbox, search_method, start_time, end_time, similarity_threshold, top_k))
        return {"code": 200, "data": {"task_id": "task-1"}}

    monkeypatch.setattr(server.person_api, "search_person_by_bbox", fake_search_person_by_bbox)

    response = post(
        "/search_person_by_bbox-http",
        json={
            "imageUrl": "http://example.test/query.jpg",
            "bbox": bbox,
            "searchMethod": "vlm",
            "startTime": "2024-12-12 07:51:15",
            "endTime": "2026-12-12 08:50:17",
            "similarityThreshold": "0.72",
            "topK": "5",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["task_id"] == "task-1"
    assert calls == [
        (
            "http://example.test/query.jpg",
            bbox,
            "vlm",
            "2024-12-12 07:51:15",
            "2026-12-12 08:50:17",
            0.72,
            5,
        )
    ]


def test_gait_feature_compare_http_route_passes_person_array(monkeypatch):
    persons = [{"id": "person_001", "isWalking": True}, {"id": "person_002", "isWalking": True}]

    async def fake_gait_feature_compare(payload):
        return {"code": 200, "data": {"similar_ids": [payload[1]["id"]]}}

    monkeypatch.setattr(server.person_api, "gait_feature_compare", fake_gait_feature_compare)

    response = post("/gait_feature_compare-http", json={"persons": persons})

    assert response.status_code == 200
    assert response.json()["data"]["similar_ids"] == ["person_002"]


def test_http_route_rejects_unknown_parameters():
    response = post("/list_cameras-http", json={"unexpected": "x"})

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "unknown parameter(s): unexpected"


def test_http_route_rejects_missing_required_parameters():
    response = post("/detect_persons-http", json={})

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "missing required parameter(s): imageUrl"


def test_http_route_rejects_invalid_boolean():
    response = post(
        "/search_recordings-http",
        json={
            "startTime": "2026-07-08T00:00:00Z",
            "endTime": "2026-07-08T00:05:00Z",
            "autoProxy": "maybe",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "autoProxy must be a boolean"
