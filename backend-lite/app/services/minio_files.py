"""MinIO 媒体文件同源代理。

人员检索（图搜图/轨迹）与文搜图的结果文档里，image_url / video_url 指向本部署
MinIO（如 http://192.168.11.194:9000/zhcs/...）。现网客户端直连 MinIO 端口会被
限速甚至阻断（与 /api/video-analysis/video 同源代理同一背景），因此后端在返回
结果前把这类绝对地址改写为同源相对路径 /api/minio/files?url=...，由前端 nginx
反代回 backend-lite，再经本模块代理到 MinIO 拉流。
"""

import logging
from urllib.parse import quote, urlsplit

import requests
from fastapi import HTTPException

from app.core.config import get_settings

logger = logging.getLogger(__name__)

OBJECT_STREAM_CONNECT_TIMEOUT_SECONDS = 10
OBJECT_STREAM_READ_TIMEOUT_SECONDS = 300

# 人员检索/文搜图结果文档里已知的 MinIO 媒体地址字段
_MEDIA_URL_KEYS = ("image_url", "video_url", "silhouette_url")


def minio_base_urls() -> tuple[str, ...]:
    """当前部署 MinIO 的全部等价基址写法（小写、无尾部斜杠）。

    MinIO 客户端地址（MINIO_ENDPOINT）常只写裸 IP/域名，而 ES 文档里的地址
    总是带端口，因此同时生成显式端口与默认端口两种写法，匹配时任一命中即可。

    Returns:
        形如 ("http://192.168.11.194:9000",) 的基址元组；未配置 endpoint 时为空。
    """
    settings = get_settings()
    endpoint = (settings.minio_endpoint or "").strip().rstrip("/")
    if not endpoint:
        return ()
    if endpoint.lower().startswith(("http://", "https://")):
        parts = urlsplit(endpoint)
        scheme = parts.scheme.lower()
        host = parts.netloc.lower()
    else:
        scheme = "https" if settings.minio_use_ssl else "http"
        host = endpoint.lower()
    if ":" in host:
        return (f"{scheme}://{host}",)
    port = int(settings.minio_port or 0) or (443 if scheme == "https" else 80)
    explicit = f"{scheme}://{host}:{port}"
    default_port = 443 if scheme == "https" else 80
    return (explicit, f"{scheme}://{host}") if port == default_port else (explicit,)


def is_minio_url(value: str) -> bool:
    """判断地址是否指向当前部署的 MinIO（仅 http(s) 绝对地址可能命中）。"""
    text = str(value or "").strip().lower()
    if not text.startswith(("http://", "https://")):
        return False
    return any(text.startswith(f"{base}/") for base in minio_base_urls())


def rewrite_minio_media_url(value: str | None) -> str | None:
    """把指向本部署 MinIO 的媒体绝对地址改写为同源代理相对路径。

    现网客户端直连 MinIO 端口会被限速甚至阻断，ES 结果文档中的 image_url /
    video_url 因此统一改写为 /api/minio/files?url=...（由 5173 nginx 反代回
    backend-lite 代理拉流）；非 MinIO 地址、相对路径、空值原样返回。

    Args:
        value: 结果文档中的媒体地址。

    Returns:
        同源代理相对路径；不匹配时返回原值。
    """
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not is_minio_url(text):
        return value
    return f"/api/minio/files?url={quote(text, safe='')}"


def rewrite_minio_media_fields(entry: dict) -> dict:
    """就地改写单条结果文档里的 MinIO 媒体地址字段（image_url/video_url/silhouette_url）。"""
    for key in _MEDIA_URL_KEYS:
        if entry.get(key):
            entry[key] = rewrite_minio_media_url(entry[key])
    return entry


def open_minio_object_stream(object_url: str, range_header: str | None) -> requests.Response:
    """打开 MinIO 对象的上游流式响应（供同源代理使用）。

    只允许当前部署 MinIO 的地址，避免本端点退化为开放代理；Range 头原样透传，
    <video> 播放器可正常 seek。调用方负责 close 返回的响应。

    Args:
        object_url: MinIO 对象绝对地址。
        range_header: 客户端 Range 请求头（无则 None）。

    Returns:
        上游流式响应。

    Raises:
        HTTPException: 地址不合法或不属于当前部署 MinIO（400），上游不可达（502）。
    """
    url = str(object_url or "").strip()
    if not url.lower().startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="url 必须是 http(s) 地址")
    if not is_minio_url(url):
        raise HTTPException(status_code=400, detail="url 不属于当前部署的 MinIO 地址")
    headers = {"Range": range_header} if range_header else {}
    try:
        return requests.get(
            url,
            headers=headers,
            stream=True,
            timeout=(OBJECT_STREAM_CONNECT_TIMEOUT_SECONDS, OBJECT_STREAM_READ_TIMEOUT_SECONDS),
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"MinIO object fetch failed: {exc}") from exc
