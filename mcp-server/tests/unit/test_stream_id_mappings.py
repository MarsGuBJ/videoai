"""流ID映射测试：StreamIdMappings 持久化/导入校验、HTTP 路由与 resolve_device_credentials 映射兜底解析。"""

import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

import app.server as server
from app.models import Camera
from app.nvr_devices import STREAM_ID_MAPPED_LABEL, resolve_device_credentials
from app.storage_bindings import StorageBindings
from app.stream_id_mappings import StreamIdMappings

BJT = timezone(timedelta(hours=8))

CVR = {"host": "172.19.200.21", "port": 8000, "username": "admin", "password": "cvr-secret"}
STREAM_ID = "405c14ed5fe147e7970485eecade27e3"


def make_camera(**overrides) -> Camera:
    now = datetime(2026, 9, 1, tzinfo=BJT)
    data = {
        "id": "cam-1",
        "name": "园区东门",
        "sourceUrl": "rtsp://admin:p%40ss@10.20.0.99:554/Streaming/Channels/101",
        "streamApp": "live",
        "streamName": "cam-1",
        "status": "RUNNING",
        "playbackUrl": "/live/cam-1.live.flv",
        "createdAt": now,
        "updatedAt": now,
        "nvrChannel": None,
        "nvrTrackId": None,
        "ip": "10.20.0.99",
    }
    data.update(overrides)
    return Camera(**data)


def make_mappings(tmp_path, camera_host="10.20.0.99", stream_id=STREAM_ID, cvr=None) -> StreamIdMappings:
    mappings = StreamIdMappings(str(tmp_path / "stream_id_mappings.json"))
    cvr = cvr or CVR
    mappings.import_rows([{"streamId": stream_id, "cameraHost": camera_host}], cvr)
    return mappings


def run(coro):
    return asyncio.run(coro)


# --- StreamIdMappings 导入校验与落盘 ---


def test_import_rows_and_get(tmp_path):
    mappings = make_mappings(tmp_path)

    mapping = mappings.get("10.20.0.99")

    assert mapping == {
        "streamId": STREAM_ID,
        "cvrHost": CVR["host"],
        "cvrPort": CVR["port"],
        "username": CVR["username"],
        "password": CVR["password"],
    }
    # key 归一化：大小写/空白不敏感
    assert mappings.get(" 10.20.0.99 ") == mapping


def test_import_rows_skips_invalid_rows(tmp_path):
    mappings = StreamIdMappings(str(tmp_path / "mappings.json"))

    result = mappings.import_rows(
        [
            {"streamId": STREAM_ID, "cameraHost": "10.20.0.99"},
            {"streamId": "***", "cameraHost": "10.20.0.100"},  # 去 * 后为空
            {"streamId": "  ", "cameraHost": "10.20.0.101"},  # 空白
            {"streamId": STREAM_ID, "cameraHost": "not-an-ip"},  # 非法 IPv4
            {"streamId": STREAM_ID, "cameraHost": ""},  # 空 cameraHost
            "not-a-dict",
        ],
        CVR,
    )

    assert result["imported"] == 1
    assert len(result["skipped"]) == 5
    assert [item["reason"] for item in result["skipped"][:3]] == [
        "streamId 为空（去除 * 与空白后）",
        "streamId 为空（去除 * 与空白后）",
        "cameraHost 不是合法 IPv4 地址: not-an-ip",
    ]
    assert mappings.get("10.20.0.99") is not None


def test_import_rows_skips_all_when_cvr_host_empty(tmp_path):
    mappings = StreamIdMappings(str(tmp_path / "mappings.json"))

    result = mappings.import_rows([{"streamId": STREAM_ID, "cameraHost": "10.20.0.99"}], {"host": ""})

    assert result["imported"] == 0
    assert result["skipped"][0]["reason"] == "cvr.host 为空"
    assert mappings.all() == []


def test_import_rows_port_defaults_to_8000(tmp_path):
    mappings = StreamIdMappings(str(tmp_path / "mappings.json"))

    mappings.import_rows(
        [{"streamId": STREAM_ID, "cameraHost": "10.20.0.99"}],
        {"host": CVR["host"], "username": "admin", "password": "cvr-secret"},
    )

    assert mappings.get("10.20.0.99")["cvrPort"] == 8000


def test_import_rows_same_camera_overwrites(tmp_path):
    mappings = make_mappings(tmp_path)

    mappings.import_rows(
        [{"streamId": "newstreamid", "cameraHost": "10.20.0.99"}],
        {"host": "172.19.200.22", "port": 9000, "username": "u2", "password": "p2"},
    )

    assert len(mappings.all()) == 1
    mapping = mappings.get("10.20.0.99")
    assert mapping["streamId"] == "newstreamid"
    assert mapping["cvrHost"] == "172.19.200.22"
    assert mapping["cvrPort"] == 9000


def test_stream_id_mappings_persist_and_reload(tmp_path):
    file_path = tmp_path / "mappings.json"
    mappings = StreamIdMappings(str(file_path))
    mappings.import_rows([{"streamId": STREAM_ID, "cameraHost": "10.20.0.99"}], CVR)

    reloaded = StreamIdMappings(str(file_path))

    assert reloaded.get("10.20.0.99")["streamId"] == STREAM_ID
    assert json.loads(file_path.read_text(encoding="utf-8"))["10.20.0.99"]["cvrHost"] == CVR["host"]
    assert not (tmp_path / "mappings.json.tmp").exists()


def test_stream_id_mappings_missing_file_starts_empty(tmp_path):
    mappings = StreamIdMappings(str(tmp_path / "does-not-exist.json"))

    assert mappings.all() == []


def test_all_excludes_password(tmp_path):
    mappings = make_mappings(tmp_path)

    listed = mappings.all()

    assert listed == [
        {
            "cameraHost": "10.20.0.99",
            "streamId": STREAM_ID,
            "cvrHost": CVR["host"],
            "cvrPort": CVR["port"],
            "username": CVR["username"],
        }
    ]
    assert CVR["password"] not in json.dumps(listed)


# --- resolve_device_credentials 流ID映射兜底 ---


class MissLookup:
    """反查永不命中的 channel_lookup。"""

    async def lookup(self, host):
        return None


def test_resolve_falls_back_to_stream_id_mapping(tmp_path):
    """反查未命中且平台无通道字段：按摄像头 ip 命中流ID映射，返回流ID凭据（通道 0）。"""
    mappings = make_mappings(tmp_path)

    credentials = run(
        resolve_device_credentials(make_camera(), MissLookup(), frozenset(), stream_id_mappings=mappings)
    )

    assert credentials.host == CVR["host"]
    assert credentials.username == CVR["username"]
    assert credentials.password == CVR["password"]
    assert credentials.sdk_port == CVR["port"]
    assert credentials.channel == 0
    assert credentials.stream_id == STREAM_ID
    assert credentials.track_id == STREAM_ID


def test_resolve_mapping_falls_back_to_source_url_host(tmp_path):
    """摄像头无平台 ip 字段时按 sourceUrl 主机匹配映射。"""
    mappings = make_mappings(tmp_path)

    credentials = run(
        resolve_device_credentials(make_camera(ip=None), MissLookup(), frozenset(), stream_id_mappings=mappings)
    )

    assert credentials.stream_id == STREAM_ID
    assert credentials.channel == 0


def test_resolve_mapping_miss_keeps_original_error(tmp_path):
    """映射未命中：仍报原"未绑定 NVR"错误（消息注明反查未命中），且不含密码。"""
    mappings = make_mappings(tmp_path, camera_host="10.20.0.100")

    with pytest.raises(ValueError, match="not bound to an NVR") as exc_info:
        run(resolve_device_credentials(make_camera(), MissLookup(), frozenset(), stream_id_mappings=mappings))
    assert "reverse lookup missed" in str(exc_info.value)
    assert CVR["password"] not in str(exc_info.value)


def test_resolve_mapping_not_used_when_camera_bound_to_nvr(tmp_path):
    """摄像头自身有 nvrTrackId（NVR 凭据可解析）：映射不生效，走原解析逻辑。"""
    mappings = make_mappings(tmp_path)
    camera = make_camera(
        sourceUrl="rtsp://admin:p%40ss@10.20.0.99:554/Streaming/Channels/101", nvrTrackId="101"
    )

    credentials = run(
        resolve_device_credentials(camera, MissLookup(), frozenset(), stream_id_mappings=mappings)
    )

    assert credentials.host == "10.20.0.99"
    assert credentials.stream_id == ""
    assert credentials.channel == 1


# --- HTTP 路由 ---


def post(path: str, payload: dict) -> httpx.Response:
    async def run_request():
        transport = httpx.ASGITransport(app=server.mcp.streamable_http_app())
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(path, json=payload)

    return asyncio.run(run_request())


def get(path: str) -> httpx.Response:
    async def run_request():
        transport = httpx.ASGITransport(app=server.mcp.streamable_http_app())
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get(path)

    return asyncio.run(run_request())


def install_tmp_mappings(monkeypatch, tmp_path) -> StreamIdMappings:
    mappings = StreamIdMappings(str(tmp_path / "stream_id_mappings.json"))
    monkeypatch.setattr("app.routes.stream_id_mappings", mappings)
    return mappings


def test_stream_id_mapping_routes_import_and_list(monkeypatch, tmp_path):
    install_tmp_mappings(monkeypatch, tmp_path)

    response = post(
        "/stream-id-mappings/import",
        {
            "rows": [
                {"streamId": STREAM_ID, "cameraHost": "10.20.0.99"},
                {"streamId": "***", "cameraHost": "10.20.0.100"},
            ],
            "cvr": CVR,
        },
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["imported"] == 1
    assert len(body["skipped"]) == 1
    assert "cvr-secret" not in response.text

    response = get("/stream-id-mappings")

    assert response.status_code == 200
    assert response.json() == {
        "data": [
            {
                "cameraHost": "10.20.0.99",
                "streamId": STREAM_ID,
                "cvrHost": CVR["host"],
                "cvrPort": 8000,
                "username": "admin",
            }
        ]
    }
    # GET 对外输出不含密码
    assert "cvr-secret" not in response.text


def test_stream_id_mapping_import_rejects_bad_payload(monkeypatch, tmp_path):
    install_tmp_mappings(monkeypatch, tmp_path)

    response = post("/stream-id-mappings/import", {"rows": "10.20.0.99", "cvr": CVR})
    assert response.status_code == 400

    response = post("/stream-id-mappings/import", {"rows": [], "cvr": "172.19.200.21"})
    assert response.status_code == 400


def test_resolved_route_marks_stream_id_mapped_camera(monkeypatch, tmp_path):
    """无显式绑定但命中流ID映射的摄像头：host 为"流ID映射"且带 streamIdMapped；其余形状不变。"""
    mappings = install_tmp_mappings(monkeypatch, tmp_path)
    mappings.import_rows([{"streamId": STREAM_ID, "cameraHost": "10.20.0.99"}], CVR)
    bindings = StorageBindings(str(tmp_path / "bindings.json"))
    monkeypatch.setattr("app.routes.storage_bindings", bindings)

    async def fake_list_cameras():
        return [
            make_camera(id="cam-mapped", ip="10.20.0.99"),
            make_camera(id="cam-plain", ip=None, sourceUrl=""),
        ]

    monkeypatch.setattr(server.videoai, "list_cameras", fake_list_cameras)

    response = get("/storage-bindings/resolved")

    assert response.status_code == 200
    assert response.json() == {
        "data": [{"cameraId": "cam-mapped", "host": STREAM_ID_MAPPED_LABEL, "bound": False, "streamIdMapped": True}]
    }
    assert "cvr-secret" not in response.text
