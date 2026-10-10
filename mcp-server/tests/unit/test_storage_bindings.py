"""录像存储绑定测试：StorageBindings 持久化、HTTP 路由与 resolve_device_credentials 绑定优先解析。"""

import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

import app.nvr_devices as nvr_devices
import app.server as server
from app.models import Camera
from app.nvr_devices import resolve_device_credentials, verify_storage_recording
from app.storage_bindings import StorageBindings

BJT = timezone(timedelta(hours=8))

BINDING = {"host": "10.20.0.10", "username": "nvr-admin", "password": "nvr-secret"}

CHANNELS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<InputProxyChannelList xmlns="http://www.hikvision.com/ver20/XMLSchema">
  <InputProxyChannel>
    <id>3</id>
    <sourceInputPortDescriptor>
      <ipAddress>10.20.0.99</ipAddress>
    </sourceInputPortDescriptor>
  </InputProxyChannel>
</InputProxyChannelList>"""

SEARCH_EMPTY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<CMSearchResult xmlns="http://www.hikvision.com/ver20/XMLSchema">
</CMSearchResult>"""


@pytest.fixture(autouse=True)
def clear_binding_channel_cache():
    # 绑定通道反查有 per-host 600s 模块级缓存，用例间必须清空
    nvr_devices._binding_channel_cache.clear()
    yield
    nvr_devices._binding_channel_cache.clear()


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
        "nvrId": "10.20.0.99",
        "nvrChannel": "1",
        "nvrTrackId": "101",
        "nvrStreamType": "main",
    }
    data.update(overrides)
    return Camera(**data)


class FakeResponse:
    def __init__(self, text: str = CHANNELS_XML, status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)


def install_fake_httpx(monkeypatch, response=None, error=None):
    calls = {}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            calls["auth"] = kwargs.get("auth")

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url):
            calls["url"] = url
            if error is not None:
                raise error
            return response or FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    return calls


def search_hit_xml() -> str:
    """相对当前时间构造一条命中检索结果，避免固定时间随运行日期漂出校验窗口被裁剪。"""
    end = datetime.now(BJT) - timedelta(hours=1)
    start = end - timedelta(hours=1)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<CMSearchResult xmlns="http://www.hikvision.com/ver20/XMLSchema">
  <searchMatchItem>
    <trackID>301</trackID>
    <startTime>{start.isoformat()}</startTime>
    <endTime>{end.isoformat()}</endTime>
  </searchMatchItem>
</CMSearchResult>"""


def install_fake_httpx_with_search(monkeypatch, channels_xml=CHANNELS_XML, search_xml=None):
    """同时伪造通道反查（GET）与录像检索（POST）：search_xml 为 None 时检索请求抛连接错误。"""
    calls = {}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url):
            calls["channels_url"] = url
            return FakeResponse(channels_xml)

        async def post(self, url, content=None, headers=None):
            calls["search_url"] = url
            if search_xml is None:
                raise httpx.ConnectError("boom")
            return FakeResponse(search_xml)

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    return calls


def run(coro):
    return asyncio.run(coro)


# --- StorageBindings 存储与落盘 ---


def test_storage_bindings_bind_get_all_and_unbind(tmp_path):
    bindings = StorageBindings(str(tmp_path / "bindings.json"))

    bound = bindings.bind([{"cameraId": "cam-1", **BINDING}, {"cameraId": "cam-2", **BINDING}])

    assert bound == 2
    # get 返回含密码的完整绑定，供内部解析用
    assert bindings.get("cam-1") == BINDING
    # all 的对外视图不含密码
    assert bindings.all() == [
        {"cameraId": "cam-1", "host": BINDING["host"], "username": BINDING["username"]},
        {"cameraId": "cam-2", "host": BINDING["host"], "username": BINDING["username"]},
    ]
    assert "password" not in json.dumps(bindings.all())
    assert bindings.unbind(["cam-1", "cam-missing"]) == 1
    assert bindings.get("cam-1") is None
    assert bindings.get("cam-2") is not None


def test_storage_bindings_same_camera_overwrites(tmp_path):
    bindings = StorageBindings(str(tmp_path / "bindings.json"))
    bindings.bind([{"cameraId": "cam-1", **BINDING}])
    bindings.bind([{"cameraId": "cam-1", "host": "10.20.0.11", "username": "u2", "password": "p2"}])

    assert len(bindings.all()) == 1
    assert bindings.get("cam-1")["host"] == "10.20.0.11"


def test_storage_bindings_persists_and_reloads(tmp_path):
    file_path = tmp_path / "bindings.json"
    StorageBindings(str(file_path)).bind([{"cameraId": "cam-1", **BINDING}])

    reloaded = StorageBindings(str(file_path))

    assert reloaded.get("cam-1") == BINDING
    # 落盘文件是合法 JSON，且不含临时文件残留
    assert json.loads(file_path.read_text(encoding="utf-8"))["cam-1"]["host"] == BINDING["host"]
    assert not (tmp_path / "bindings.json.tmp").exists()


def test_storage_bindings_missing_file_starts_empty(tmp_path):
    bindings = StorageBindings(str(tmp_path / "does-not-exist.json"))

    assert bindings.all() == []


def test_storage_bindings_unbind_persists(tmp_path):
    file_path = tmp_path / "bindings.json"
    bindings = StorageBindings(str(file_path))
    bindings.bind([{"cameraId": "cam-1", **BINDING}])

    assert bindings.unbind(["cam-1"]) == 1
    assert StorageBindings(str(file_path)).all() == []


# --- resolve_device_credentials 绑定优先 ---


def test_binding_channel_lookup_hit_overrides_host_and_credentials(monkeypatch):
    """绑定命中：主机/凭据取自绑定，通道按 sourceUrl 的 IP 反查绑定设备得出。"""
    calls = install_fake_httpx(monkeypatch)
    camera = make_camera()

    credentials = run(resolve_device_credentials(camera, None, frozenset(), binding=BINDING))

    assert calls["url"] == "http://10.20.0.10/ISAPI/ContentMgmt/InputProxy/channels"
    assert isinstance(calls["auth"], httpx.DigestAuth)
    assert credentials.host == "10.20.0.10"
    assert credentials.username == "nvr-admin"
    assert credentials.password == "nvr-secret"
    assert credentials.channel == 3
    assert credentials.track_id == "301"


def test_binding_lookup_miss_falls_back_to_nvr_track_id(monkeypatch):
    """绑定设备上反查不到该 IPC：回退平台 nvrTrackId，主机/凭据仍用绑定的。"""
    install_fake_httpx(monkeypatch)
    camera = make_camera(
        sourceUrl="rtsp://admin:p%40ss@10.20.0.77:554/Streaming/Channels/101", nvrChannel=None, nvrTrackId="201"
    )

    credentials = run(resolve_device_credentials(camera, None, frozenset(), binding=BINDING))

    assert credentials.host == "10.20.0.10"
    assert credentials.username == "nvr-admin"
    assert credentials.channel == 2
    assert credentials.track_id == "201"


def test_binding_lookup_request_failure_falls_back_to_nvr_track_id(monkeypatch):
    """绑定设备不可达：同样回退平台通道字段。"""
    install_fake_httpx(monkeypatch, error=httpx.ConnectError("boom"))

    credentials = run(resolve_device_credentials(make_camera(), None, frozenset(), binding=BINDING))

    assert credentials.host == "10.20.0.10"
    assert credentials.channel == 1
    assert credentials.track_id == "101"


def test_binding_without_any_channel_info_raises(monkeypatch):
    """反查未命中且平台也未配置通道字段时报错，消息注明关联存储设备。"""
    install_fake_httpx(monkeypatch)
    camera = make_camera(
        sourceUrl="rtsp://admin:p%40ss@10.20.0.77:554/Streaming/Channels/101",
        nvrChannel=None,
        nvrTrackId=None,
    )

    with pytest.raises(ValueError, match="未在关联存储设备 10.20.0.10 上反查到通道") as exc_info:
        run(resolve_device_credentials(camera, None, frozenset(), binding=BINDING))
    assert "nvr-secret" not in str(exc_info.value)


def test_binding_channel_lookup_uses_cache(monkeypatch):
    """同一主机 TTL 内只拉取一次通道列表。"""
    calls = install_fake_httpx(monkeypatch)
    camera = make_camera()

    run(resolve_device_credentials(camera, None, frozenset(), binding=BINDING))
    first_url = calls["url"]
    calls.clear()
    run(resolve_device_credentials(camera, None, frozenset(), binding=BINDING))

    assert first_url.endswith("/ISAPI/ContentMgmt/InputProxy/channels")
    assert "url" not in calls


def test_no_binding_keeps_original_parse():
    """未绑定时走原逻辑：凭据与通道来自摄像头自身字段。"""
    credentials = run(resolve_device_credentials(make_camera(), None, frozenset()))

    assert credentials.host == "10.20.0.99"
    assert credentials.username == "admin"
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


def install_tmp_bindings(monkeypatch, tmp_path) -> StorageBindings:
    bindings = StorageBindings(str(tmp_path / "bindings.json"))
    monkeypatch.setattr("app.routes.storage_bindings", bindings)
    return bindings


def install_bind_verify_passthrough(monkeypatch, reasons: dict[str, str | None] | None = None):
    """让 bind 路由的摄像头列表与录像校验可控：reasons 按 cameraId 给出跳过原因（缺省通过）。"""
    reasons = reasons or {}

    async def fake_list_cameras():
        return [make_camera(id="cam-1"), make_camera(id="cam-2")]

    async def fake_verify(camera, host, username, password):
        return reasons.get(camera.id)

    monkeypatch.setattr(server.videoai, "list_cameras", fake_list_cameras)
    monkeypatch.setattr("app.routes.verify_storage_recording", fake_verify)


def test_storage_binding_routes_bind_list_unbind(monkeypatch, tmp_path):
    bindings = install_tmp_bindings(monkeypatch, tmp_path)
    install_bind_verify_passthrough(monkeypatch)

    response = post(
        "/storage-bindings/bind",
        {"items": [{"cameraId": "cam-1", "host": "10.20.0.10", "username": "admin", "password": "secret"}]},
    )

    assert response.status_code == 200
    assert response.json() == {"data": {"bound": 1, "skipped": []}}
    # 绑定已落盘
    assert json.loads((tmp_path / "bindings.json").read_text(encoding="utf-8"))["cam-1"]["host"] == "10.20.0.10"

    response = get("/storage-bindings")

    assert response.status_code == 200
    assert response.json() == {"data": [{"cameraId": "cam-1", "host": "10.20.0.10", "username": "admin"}]}
    # GET 对外输出不含密码
    assert "secret" not in response.text

    response = post("/storage-bindings/unbind", {"cameraIds": ["cam-1"]})

    assert response.status_code == 200
    assert response.json() == {"data": {"unbound": 1}}
    assert bindings.all() == []


def test_storage_binding_bind_skips_devices_without_recordings(monkeypatch, tmp_path):
    """校验未通过的设备不绑定也不落盘，在 skipped 中返回原因。"""
    bindings = install_tmp_bindings(monkeypatch, tmp_path)
    install_bind_verify_passthrough(monkeypatch, {"cam-2": "存储设备 10.20.0.10 上最近 30 天查询不到该摄像头的录像"})

    response = post(
        "/storage-bindings/bind",
        {
            "items": [
                {"cameraId": "cam-1", "host": "10.20.0.10", "username": "admin", "password": "secret"},
                {"cameraId": "cam-2", "host": "10.20.0.10", "username": "admin", "password": "secret"},
            ]
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "data": {
            "bound": 1,
            "skipped": [{"cameraId": "cam-2", "reason": "存储设备 10.20.0.10 上最近 30 天查询不到该摄像头的录像"}],
        }
    }
    assert [item["cameraId"] for item in bindings.all()] == ["cam-1"]


def test_storage_binding_bind_skips_unknown_camera(monkeypatch, tmp_path):
    """平台设备列表中不存在的 cameraId 直接跳过。"""
    bindings = install_tmp_bindings(monkeypatch, tmp_path)
    install_bind_verify_passthrough(monkeypatch)

    response = post(
        "/storage-bindings/bind",
        {"items": [{"cameraId": "cam-ghost", "host": "10.20.0.10", "username": "admin", "password": "secret"}]},
    )

    assert response.status_code == 200
    assert response.json()["data"]["bound"] == 0
    assert response.json()["data"]["skipped"] == [{"cameraId": "cam-ghost", "reason": "摄像头不存在或已删除"}]
    assert bindings.all() == []


def test_storage_binding_bind_rejects_empty_fields(monkeypatch, tmp_path):
    install_tmp_bindings(monkeypatch, tmp_path)

    response = post(
        "/storage-bindings/bind",
        {"items": [{"cameraId": "cam-1", "host": "", "username": "admin", "password": "secret"}]},
    )

    assert response.status_code == 400
    assert "non-empty" in response.json()["error"]["message"]
    assert "secret" not in response.text


def test_storage_binding_bind_rejects_non_list_items(monkeypatch, tmp_path):
    install_tmp_bindings(monkeypatch, tmp_path)

    response = post("/storage-bindings/bind", {"items": "cam-1"})

    assert response.status_code == 400


def test_storage_binding_unbind_rejects_non_list(monkeypatch, tmp_path):
    install_tmp_bindings(monkeypatch, tmp_path)

    response = post("/storage-bindings/unbind", {"cameraIds": "cam-1"})

    assert response.status_code == 400


# --- verify_storage_recording 绑定前录像校验 ---


def test_verify_passes_when_channel_and_recordings_found(monkeypatch):
    """通道反查命中且最近窗口内有录像：校验通过。"""
    calls = install_fake_httpx_with_search(monkeypatch, search_xml=search_hit_xml())

    reason = run(verify_storage_recording(make_camera(), BINDING["host"], BINDING["username"], BINDING["password"]))

    assert reason is None
    assert calls["channels_url"] == "http://10.20.0.10/ISAPI/ContentMgmt/InputProxy/channels"
    assert calls["search_url"] == "http://10.20.0.10/ISAPI/ContentMgmt/search"


def test_verify_fails_when_channel_not_on_storage(monkeypatch):
    """存储设备输入通道列表中没有该 IPC：不发起检索，直接返回原因。"""
    calls = install_fake_httpx_with_search(monkeypatch, search_xml=search_hit_xml())
    camera = make_camera(sourceUrl="rtsp://admin:p%40ss@10.20.0.77:554/Streaming/Channels/101")

    reason = run(verify_storage_recording(camera, BINDING["host"], BINDING["username"], BINDING["password"]))

    assert reason is not None
    assert "10.20.0.77" in reason
    assert "通道" in reason
    assert "search_url" not in calls


def test_verify_fails_when_no_recordings(monkeypatch):
    """通道存在但最近窗口内检索不到录像：返回原因。"""
    install_fake_httpx_with_search(monkeypatch, search_xml=SEARCH_EMPTY_XML)

    reason = run(verify_storage_recording(make_camera(), BINDING["host"], BINDING["username"], BINDING["password"]))

    assert reason is not None
    assert "查询不到" in reason


def test_verify_fails_when_search_unreachable(monkeypatch):
    """录像检索请求失败：原因来自 NvrDeviceError，且不含密码。"""
    install_fake_httpx_with_search(monkeypatch, search_xml=None)

    reason = run(verify_storage_recording(make_camera(), BINDING["host"], BINDING["username"], BINDING["password"]))

    assert reason is not None
    assert BINDING["password"] not in reason


def test_verify_fails_without_source_url(monkeypatch):
    """摄像头无 sourceUrl：无法定位通道，直接返回原因。"""
    install_fake_httpx_with_search(monkeypatch, search_xml=search_hit_xml())

    reason = run(
        verify_storage_recording(make_camera(sourceUrl=""), BINDING["host"], BINDING["username"], BINDING["password"])
    )

    assert reason is not None
    assert "sourceUrl" in reason


# --- 流ID绑定（现场 DS-A CVR：ISAPI 关闭、通道回放不可用，按流ID直接回放） ---

STREAM_BINDING = {
    "host": "172.19.200.21",
    "username": "admin",
    "password": "nvr-secret",
    "streamId": "405c14ed5fe147e7970485eecade27e3",
}


def test_storage_bindings_stream_id_roundtrip(tmp_path):
    """带 streamId 的绑定：get/all 暴露、落盘并可重载。"""
    file_path = tmp_path / "bindings.json"
    bindings = StorageBindings(str(file_path))

    bindings.bind([{"cameraId": "cam-1", **STREAM_BINDING}])

    assert bindings.get("cam-1") == STREAM_BINDING
    assert bindings.all() == [
        {
            "cameraId": "cam-1",
            "host": STREAM_BINDING["host"],
            "username": STREAM_BINDING["username"],
            "streamId": STREAM_BINDING["streamId"],
        }
    ]
    reloaded = StorageBindings(str(file_path))
    assert reloaded.get("cam-1") == STREAM_BINDING
    # 密码绝不进对外视图
    assert "nvr-secret" not in json.dumps(bindings.all())


def test_storage_bindings_without_stream_id_omits_key(tmp_path):
    """旧格式绑定（无 streamId）：get/all 不出现 streamId 字段，保持对外形状兼容。"""
    bindings = StorageBindings(str(tmp_path / "bindings.json"))
    bindings.bind([{"cameraId": "cam-1", **BINDING}])

    assert bindings.get("cam-1") == BINDING
    assert bindings.all() == [
        {"cameraId": "cam-1", "host": BINDING["host"], "username": BINDING["username"]}
    ]


def test_binding_with_stream_id_skips_isapi_lookup(monkeypatch):
    """绑定带流ID：不做 ISAPI 通道反查（这类设备 ISAPI 已关闭），直接返回流ID凭据。"""
    async def forbidden_lookup(*args, **kwargs):
        raise AssertionError("stream-id binding must not call ISAPI channel lookup")

    monkeypatch.setattr(nvr_devices, "lookup_bound_storage_channel", forbidden_lookup)
    camera = make_camera(
        sourceUrl="rtsp://admin:cisdi2024@172.19.102.23:554/Streaming/Channels/101",
        nvrChannel=None,
        nvrTrackId=None,
    )

    credentials = run(resolve_device_credentials(camera, None, frozenset(), binding=STREAM_BINDING))

    assert credentials.host == "172.19.200.21"
    assert credentials.stream_id == STREAM_BINDING["streamId"]
    assert credentials.track_id == STREAM_BINDING["streamId"]
    assert credentials.channel == 0


def test_bind_route_with_stream_id_skips_recording_verification(monkeypatch, tmp_path):
    """带 streamId 的绑定项跳过录像校验直接绑定（映射来自 CVR 流源导出，视为权威）。"""
    bindings = install_tmp_bindings(monkeypatch, tmp_path)

    async def forbidden_verify(camera, host, username, password):
        raise AssertionError("stream-id bind must not verify recordings via ISAPI")

    async def fake_list_cameras():
        return [make_camera(id="cam-1")]

    monkeypatch.setattr(server.videoai, "list_cameras", fake_list_cameras)
    monkeypatch.setattr("app.routes.verify_storage_recording", forbidden_verify)

    response = post(
        "/storage-bindings/bind",
        {
            "items": [
                {
                    "cameraId": "cam-1",
                    "host": STREAM_BINDING["host"],
                    "username": STREAM_BINDING["username"],
                    "password": STREAM_BINDING["password"],
                    "streamId": STREAM_BINDING["streamId"],
                }
            ]
        },
    )

    assert response.status_code == 200
    assert response.json() == {"data": {"bound": 1, "skipped": []}}
    assert bindings.get("cam-1") == STREAM_BINDING
    listed = get("/storage-bindings").json()["data"]
    assert listed[0]["streamId"] == STREAM_BINDING["streamId"]
