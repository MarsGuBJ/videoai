import logging
import os
from dataclasses import dataclass
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _env(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _env_csv(name: str, default: str) -> tuple[str, ...]:
    return tuple(value.strip() for value in _env(name, default).split(",") if value.strip())


def _env_csv_or(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    """逗号分隔列表；未设置或显式置空时用默认值（录像设备默认按部署网段自动选择）。"""
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return tuple(value.strip() for value in raw.split(",") if value.strip())


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")


@dataclass(frozen=True)
class Settings:
    videoai_base_url: str
    videoai_media_base_url: str
    person_api_base_url: str
    retrieve_api_base_url: str
    retrieve_api_timeout_seconds: float
    video_understanding_api_base_url: str
    video_understanding_timeout_seconds: float
    zlm_http_url: str
    zlm_public_http_url: str
    zlm_secret: str
    zlm_rtmp_push_base: str
    hikvision_base_url: str
    hikvision_username: str
    hikvision_password: str
    hcnetsdk_host: str
    hcnetsdk_port: int
    hcnetsdk_username: str
    hcnetsdk_password: str
    hcnetsdk_channel: int
    hcnetsdk_download_nvr_hosts: tuple[str, ...]
    hcnetsdk_download_port: int
    hcnetsdk_download_username: str
    hcnetsdk_download_password: str
    hcnetsdk_download_channel: int
    cvr_hosts: tuple[str, ...]
    cvr_username: str
    cvr_password: str
    hcnetsdk_max_live_sessions: int
    minio_endpoint: str
    minio_port: int
    minio_use_ssl: bool
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    playback_ttl_seconds: int
    request_timeout_seconds: float
    recording_fallback_file: str
    mcp_host: str
    mcp_port: int
    mcp_transport: str
    mcp_public_base_url: str
    camera_import_username: str
    camera_import_password: str
    camera_import_backend_url: str


# 部署网段 → 默认录像设备（NVR 下载白名单, CVR 集群）：
# 不同环境使用不同的 NVR/CVR，网段取自 MCP 对外基址（VIDEOAI_MCP_PUBLIC_BASE_URL）主机地址
# 的第一段；今后新增环境时在 _ENV_DEVICE_DEFAULTS 追加一行即可。
_ENV_DEVICE_DEFAULTS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    # 网段: (NVR 白名单, CVR 集群)
    "10": (("10.10.7.252", "10.10.7.253"), ()),
    "172": ((), ("172.21.200.21", "172.21.200.22", "172.21.200.23")),
}
# 未知网段（域名/本机地址等）的兜底：保持历史默认（NVR+CVR 全配），避免新环境起不来
_LEGACY_NVR_HOSTS = ("10.10.7.252", "10.10.7.253")
_LEGACY_CVR_HOSTS = ("172.21.200.21", "172.21.200.22", "172.21.200.23")


def _server_segment(public_base_url: str) -> str:
    """MCP 对外基址主机地址的第一段数字（如 10/172）；非 IP 主机名返回空串。"""
    host = urlparse(public_base_url).hostname or ""
    segment = host.split(".", 1)[0]
    return segment if segment.isdigit() else ""


def _env_device_defaults(public_base_url: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """按部署网段返回默认 (NVR 白名单, CVR 集群)；未知网段保持历史默认并告警提示补充映射。"""
    segment = _server_segment(public_base_url)
    if segment in _ENV_DEVICE_DEFAULTS:
        return _ENV_DEVICE_DEFAULTS[segment]
    logger.warning(
        "unknown deploy segment %r from MCP public base url %s; using legacy NVR/CVR defaults"
        " — add the environment to _ENV_DEVICE_DEFAULTS in app/settings.py",
        segment or "(non-IP host)",
        public_base_url,
    )
    return _LEGACY_NVR_HOSTS, _LEGACY_CVR_HOSTS


def load_settings() -> Settings:
    # 下列 192.168.x.x / 10.x.x.x 默认值为部署内网地址，均可用对应环境变量覆盖
    mcp_public_base_url = _env("VIDEOAI_MCP_PUBLIC_BASE_URL", "http://192.168.11.194:8097").rstrip("/")
    default_nvr_hosts, default_cvr_hosts = _env_device_defaults(mcp_public_base_url)
    return Settings(
        videoai_base_url=_env("VIDEOAI_BACKEND_URL", "http://localhost:8081").rstrip("/"),
        videoai_media_base_url=(
            _env("VIDEOAI_MEDIA_BACKEND_URL", "") or _env("VIDEOAI_BACKEND_URL", "http://localhost:8081")
        ).rstrip("/"),
        person_api_base_url=_env("PERSON_API_BASE_URL", "http://10.10.3.100:15501").rstrip("/"),
        retrieve_api_base_url=_env("RETRIEVE_API_BASE_URL", "http://10.10.3.100:15000").rstrip("/"),
        retrieve_api_timeout_seconds=float(_env("RETRIEVE_API_TIMEOUT_SECONDS", "120")),
        video_understanding_api_base_url=_env("VIDEO_UNDERSTANDING_API_BASE_URL", "http://10.10.3.100:8780").rstrip("/"),
        video_understanding_timeout_seconds=float(_env("VIDEO_UNDERSTANDING_TIMEOUT_SECONDS", "600")),
        zlm_http_url=_env("VIDEOAI_ZLM_HTTP_URL", "http://127.0.0.1:8082").rstrip("/"),
        zlm_public_http_url=_env("VIDEOAI_ZLM_PUBLIC_HTTP_URL", "http://192.168.11.194:9100").rstrip("/"),
        zlm_secret=_env("VIDEOAI_ZLM_SECRET", "TFtkiHhkoFJzgamQXuYY1zACl2XYSnUR"),
        zlm_rtmp_push_base=_env("VIDEOAI_ZLM_RTMP_PUSH_BASE", "rtmp://127.0.0.1:1945/live").rstrip("/"),
        hikvision_base_url=_env("HIKVISION_NVR_BASE_URL", "").rstrip("/"),
        hikvision_username=_env("HIKVISION_NVR_USERNAME", ""),
        hikvision_password=_env("HIKVISION_NVR_PASSWORD", ""),
        hcnetsdk_host=_env("HCNETSDK_HOST", "192.168.11.198"),
        hcnetsdk_port=_env_int("HCNETSDK_PORT", 8000),
        hcnetsdk_username=_env("HCNETSDK_USERNAME", "admin"),
        hcnetsdk_password=_env("HCNETSDK_PASSWORD", "cisdi123"),
        hcnetsdk_channel=_env_int("HCNETSDK_CHANNEL", 1),
        # 置空（或不设置）时按部署网段取默认 NVR 白名单（见 _ENV_DEVICE_DEFAULTS）
        hcnetsdk_download_nvr_hosts=_env_csv_or("HCNETSDK_DOWNLOAD_NVR_HOSTS", default_nvr_hosts),
        hcnetsdk_download_port=_env_int("HCNETSDK_DOWNLOAD_PORT", 8000),
        hcnetsdk_download_username=_env("HCNETSDK_DOWNLOAD_USERNAME", "admin"),
        hcnetsdk_download_password=_env("HCNETSDK_DOWNLOAD_PASSWORD", ""),
        hcnetsdk_download_channel=_env_int("HCNETSDK_DOWNLOAD_CHANNEL", 1),
        # CVR 中心存储（DS-A80348S）：凭据与 NVR 不同，反查命中时按设备取凭据；
        # 置空（或不设置）时按部署网段取默认 CVR 集群（见 _ENV_DEVICE_DEFAULTS）
        cvr_hosts=_env_csv_or("CVR_HOSTS", default_cvr_hosts),
        cvr_username=_env("CVR_USERNAME", "admin"),
        cvr_password=_env("CVR_PASSWORD", "Sdtjh@2025"),
        # 每台设备同时保持的 SDK 回放会话上限；0 表示不限制（demo 环境 NVR 并发受限时才设，如 2）
        hcnetsdk_max_live_sessions=_env_int("HCNETSDK_MAX_LIVE_SESSIONS", 0),
        minio_endpoint=_env("MINIO_ENDPOINT", "192.168.11.194"),
        minio_port=_env_int("MINIO_PORT", 9000),
        minio_use_ssl=_env_bool("MINIO_USE_SSL", False),
        minio_access_key=_env("MINIO_ACCESS_KEY", "minio"),
        minio_secret_key=_env("MINIO_SECRET_KEY", "Klg4dM9F3H"),
        minio_bucket=_env("MINIO_BUCKET", "public"),
        playback_ttl_seconds=_env_int("VIDEOAI_MCP_PLAYBACK_TTL_SECONDS", 1800),
        request_timeout_seconds=float(_env("VIDEOAI_MCP_REQUEST_TIMEOUT_SECONDS", "15")),
        recording_fallback_file=_env("VIDEOAI_MCP_RECORDING_FALLBACK_FILE", ""),
        # 容器内需监听所有接口，可用 VIDEOAI_MCP_HOST 覆盖
        mcp_host=_env("VIDEOAI_MCP_HOST", "0.0.0.0"),  # noqa: S104
        mcp_port=_env_int("VIDEOAI_MCP_PORT", 8097),
        mcp_transport=_env("VIDEOAI_MCP_TRANSPORT", "streamable-http"),
        # 录像动态链接（/recording-live）对外暴露的 MCP 访问基址（同时用于推断部署网段）
        mcp_public_base_url=mcp_public_base_url,
        camera_import_username=_env("CAMERA_IMPORT_USERNAME", ""),
        # 口令不做 strip，保持与原 CLI 读取语义一致
        camera_import_password=os.getenv("CAMERA_IMPORT_PASSWORD", ""),
        camera_import_backend_url=(
            _env("VIDEOAI_MEDIA_BACKEND_URL", "") or _env("VIDEOAI_BACKEND_URL", "http://backend:8081")
        ).rstrip("/"),
    )
