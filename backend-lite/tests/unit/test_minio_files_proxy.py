"""MinIO 媒体文件同源代理测试。

背景：人员检索/文搜图结果文档里的 image_url / video_url 指向本部署 MinIO，
现网客户端直连 MinIO 端口会被限速甚至阻断，后端返回前须改写为同源代理路径
/api/minio/files?url=...，由 nginx 反代回 backend-lite 代理拉流。
"""

from types import SimpleNamespace
from urllib.parse import quote

import pytest
import requests
from fastapi.testclient import TestClient

from app.api.routers import person_search as person_search_router
from app.services import minio_files

MINIO_BASE = "http://192.168.11.194:9000"


def _proxy_path(url: str) -> str:
    return f"/api/minio/files?url={quote(url, safe='')}"


def _stub_settings(endpoint="192.168.11.194", port=9000, use_ssl=False):
    return SimpleNamespace(minio_endpoint=endpoint, minio_port=port, minio_use_ssl=use_ssl)


def test_rewrite_minio_url_to_same_origin_proxy(monkeypatch: pytest.MonkeyPatch):
    """本部署 MinIO 的绝对地址改写为同源代理相对路径，原地址编码进查询参数。"""
    monkeypatch.setattr(minio_files, "get_settings", lambda: _stub_settings())
    value = f"{MINIO_BASE}/zhcs/event/image/202610/a.jpg"
    assert minio_files.rewrite_minio_media_url(value) == _proxy_path(value)


def test_rewrite_keeps_non_minio_and_relative_values(monkeypatch: pytest.MonkeyPatch):
    """非本部署 MinIO 地址（外部图床、后端自身、相对路径、空值）一律原样返回。"""
    monkeypatch.setattr(minio_files, "get_settings", lambda: _stub_settings())
    for value in (
        "https://example.com/a.jpg",
        "http://192.168.11.195:9000/zhcs/a.jpg",  # 其他主机的 MinIO 风格地址
        "http://192.168.11.194:8081/api/assets/query-images/a.jpg",  # backend 自身
        "/api/assets/query-images/a.jpg",
        "data:image/jpeg;base64,AAAA",
        "",
        None,
    ):
        assert minio_files.rewrite_minio_media_url(value) == value


def test_rewrite_matches_default_port_variant(monkeypatch: pytest.MonkeyPatch):
    """endpoint 不带端口且为默认端口时，无端口写法也视为同一 MinIO。"""
    monkeypatch.setattr(minio_files, "get_settings", lambda: _stub_settings("oss.example.com", 80, False))
    value = "http://oss.example.com/bucket/a.jpg"
    assert minio_files.rewrite_minio_media_url(value) == _proxy_path(value)
    # 非默认端口时无端口写法不命中
    monkeypatch.setattr(minio_files, "get_settings", lambda: _stub_settings("oss.example.com", 9000, False))
    assert minio_files.rewrite_minio_media_url(value) == value


def test_rewrite_accepts_endpoint_with_scheme(monkeypatch: pytest.MonkeyPatch):
    """MINIO_ENDPOINT 带 scheme 写法时同样命中。"""
    monkeypatch.setattr(minio_files, "get_settings", lambda: _stub_settings("http://192.168.11.194", 9000, False))
    value = f"{MINIO_BASE}/zhcs/a.jpg"
    assert minio_files.rewrite_minio_media_url(value) == _proxy_path(value)


def test_rewrite_media_fields_only_touches_known_keys(monkeypatch: pytest.MonkeyPatch):
    """rewrite_minio_media_fields 只改写媒体字段，其他字段原样保留。"""
    monkeypatch.setattr(minio_files, "get_settings", lambda: _stub_settings())
    entry = {
        "image_url": f"{MINIO_BASE}/zhcs/a.jpg",
        "video_url": f"{MINIO_BASE}/zhcs/a.mp4",
        "silhouette_url": None,
        "camera_locate": "12楼走廊01",
        "similarity_score": 0.87,
    }
    rewritten = minio_files.rewrite_minio_media_fields(entry)
    assert rewritten["image_url"] == _proxy_path(f"{MINIO_BASE}/zhcs/a.jpg")
    assert rewritten["video_url"] == _proxy_path(f"{MINIO_BASE}/zhcs/a.mp4")
    assert rewritten["silhouette_url"] is None
    assert rewritten["camera_locate"] == "12楼走廊01"
    assert rewritten["similarity_score"] == 0.87


class FakeStreamResponse:
    def __init__(self, chunks=(b"ab", b"cd"), status_code=200, headers=None):
        self._chunks = chunks
        self.status_code = status_code
        self.headers = headers or {}
        self.closed = False

    def iter_content(self, chunk_size):
        return iter(self._chunks)

    def close(self):
        self.closed = True


def test_minio_file_proxy_streams_with_passthrough_headers(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """代理 MinIO 对象：内容头透传、状态码原样、响应体流式输出。"""
    monkeypatch.setattr(minio_files, "get_settings", lambda: _stub_settings())
    upstream = FakeStreamResponse(
        status_code=200,
        headers={"Content-Type": "image/jpeg", "Content-Length": "4", "ETag": '"xyz"'},
    )
    captured = {}

    def fake_get(url, headers, stream, timeout):
        captured["url"] = url
        captured["headers"] = headers
        return upstream

    monkeypatch.setattr(requests, "get", fake_get)
    object_url = f"{MINIO_BASE}/zhcs/event/image/202610/a.jpg"
    response = client.get(f"/api/minio/files?url={object_url}")

    assert response.status_code == 200
    assert response.content == b"abcd"
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["content-length"] == "4"
    assert captured["url"] == object_url
    assert captured["headers"] == {}
    assert upstream.closed is True


def test_minio_file_proxy_forwards_range_header(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """客户端 Range 头原样透传，206 与 content-range 原样返回（<video> seek 依赖）。"""
    monkeypatch.setattr(minio_files, "get_settings", lambda: _stub_settings())
    upstream = FakeStreamResponse(
        status_code=206,
        headers={"Content-Type": "video/mp4", "Content-Range": "bytes 0-3/280778"},
    )
    captured = {}

    def fake_get(url, headers, stream, timeout):
        captured["headers"] = headers
        return upstream

    monkeypatch.setattr(requests, "get", fake_get)
    object_url = f"{MINIO_BASE}/zhcs/event/video/202610/a.mp4"
    response = client.get(f"/api/minio/files?url={object_url}", headers={"Range": "bytes=0-3"})

    assert response.status_code == 206
    assert response.headers["content-range"] == "bytes 0-3/280778"
    assert captured["headers"] == {"Range": "bytes=0-3"}


def test_minio_file_proxy_rejects_non_minio_url(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """非本部署 MinIO 的地址一律 400，避免退化为开放代理。"""
    monkeypatch.setattr(minio_files, "get_settings", lambda: _stub_settings())

    def fake_get(url, headers, stream, timeout):  # pragma: no cover - 不应被调用
        raise AssertionError("requests.get 不应被调用")

    monkeypatch.setattr(requests, "get", fake_get)
    response = client.get("/api/minio/files?url=https://example.com/a.jpg")
    assert response.status_code == 400


def test_minio_file_proxy_upstream_unavailable(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """MinIO 不可达时返回 502。"""
    monkeypatch.setattr(minio_files, "get_settings", lambda: _stub_settings())

    def fake_get(url, headers, stream, timeout):
        raise requests.ConnectionError("refused")

    monkeypatch.setattr(requests, "get", fake_get)
    response = client.get(f"/api/minio/files?url={MINIO_BASE}/zhcs/a.jpg")
    assert response.status_code == 502


def test_person_search_result_rewrites_minio_media_urls(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """以图搜人结果（详版全量文档）：image_url/video_url 改写为同源代理路径。"""
    monkeypatch.setattr(minio_files, "get_settings", lambda: _stub_settings())

    def fake_person_api_get(path):
        return {
            "code": "00000",
            "data": {
                "data": {
                    "status": "success",
                    "result": {
                        "similar_persons": [
                            {
                                "image_url": f"{MINIO_BASE}/zhcs/event/image/202610/a.jpg",
                                "video_url": f"{MINIO_BASE}/zhcs/event/video/202610/a.mp4",
                                "camera_locate": "12楼走廊01",
                            }
                        ]
                    },
                }
            },
        }

    monkeypatch.setattr(person_search_router, "person_api_get", fake_person_api_get)
    response = client.get("/api/person-search/results/task-1")

    assert response.status_code == 200
    persons = response.json()["data"]["data"]["result"]["similar_persons"]
    assert persons[0]["image_url"] == _proxy_path(f"{MINIO_BASE}/zhcs/event/image/202610/a.jpg")
    assert persons[0]["video_url"] == _proxy_path(f"{MINIO_BASE}/zhcs/event/video/202610/a.mp4")
    assert persons[0]["camera_locate"] == "12楼走廊01"


def test_text_search_rewrites_minio_media_urls(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """文搜图结果：items[].payload 里的 MinIO 媒体地址同样改写。"""
    monkeypatch.setattr(minio_files, "get_settings", lambda: _stub_settings())

    def fake_retrieve_api_post(path, payload):
        return {
            "code": 200,
            "data": {
                "items": [
                    {
                        "document_id": "doc-1",
                        "payload": {
                            "image_url": f"{MINIO_BASE}/zhcs/event/image/202610/a.jpg",
                            "video_url": f"{MINIO_BASE}/zhcs/event/video/202610/a.mp4",
                        },
                    },
                    {"document_id": "doc-2", "payload": {"image_url": "https://example.com/b.jpg"}},
                ]
            },
        }

    monkeypatch.setattr(person_search_router, "retrieve_api_post", fake_retrieve_api_post)
    response = client.post("/api/text-search/query", json={"message": "穿黑色上衣的人"})

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert items[0]["payload"]["image_url"] == _proxy_path(f"{MINIO_BASE}/zhcs/event/image/202610/a.jpg")
    assert items[0]["payload"]["video_url"] == _proxy_path(f"{MINIO_BASE}/zhcs/event/video/202610/a.mp4")
    assert items[1]["payload"]["image_url"] == "https://example.com/b.jpg"


def test_person_search_drops_entries_without_image_url(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """上游偶发返回不带图片地址的残缺文档：无图条目被丢弃，不再渲染成裂图卡片。"""
    monkeypatch.setattr(minio_files, "get_settings", lambda: _stub_settings())

    def fake_person_api_get(path):
        return {
            "code": "00000",
            "data": {
                "data": {
                    "status": "success",
                    "result": {
                        "similar_persons": [
                            {"image_url": f"{MINIO_BASE}/zhcs/event/image/202610/a.jpg", "similarity_score": 0.98},
                            {"image_url": "", "similarity_score": 0.9},
                            {"similarity_score": 0.88},
                            "not-a-dict",
                        ]
                    },
                }
            },
        }

    monkeypatch.setattr(person_search_router, "person_api_get", fake_person_api_get)
    response = client.get("/api/person-search/results/task-1")

    persons = response.json()["data"]["data"]["result"]["similar_persons"]
    assert len(persons) == 1
    assert persons[0]["similarity_score"] == 0.98
    assert persons[0]["image_url"] == _proxy_path(f"{MINIO_BASE}/zhcs/event/image/202610/a.jpg")


def test_text_search_drops_items_without_image_url(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """文搜图：payload 无图片地址的条目同样丢弃，其余条目不受影响。"""
    monkeypatch.setattr(minio_files, "get_settings", lambda: _stub_settings())

    def fake_retrieve_api_post(path, payload):
        return {
            "code": 200,
            "data": {
                "items": [
                    {"document_id": "doc-1", "payload": {"image_url": f"{MINIO_BASE}/zhcs/a.jpg"}},
                    {"document_id": "doc-2", "payload": {"image_url": ""}},
                    {"document_id": "doc-3", "payload": {"video_url": f"{MINIO_BASE}/zhcs/a.mp4"}},
                ]
            },
        }

    monkeypatch.setattr(person_search_router, "retrieve_api_post", fake_retrieve_api_post)
    response = client.post("/api/text-search/query", json={"message": "穿黑色上衣的人"})

    items = response.json()["data"]["items"]
    assert [it["document_id"] for it in items] == ["doc-1"]
    assert items[0]["payload"]["image_url"] == _proxy_path(f"{MINIO_BASE}/zhcs/a.jpg")
