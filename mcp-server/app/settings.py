import os
from dataclasses import dataclass


def _env(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _env_csv(name: str, default: str) -> tuple[str, ...]:
    return tuple(value.strip() for value in _env(name, default).split(",") if value.strip())


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


def load_settings() -> Settings:
    # 下列 192.168.x.x / 10.x.x.x 默认值为部署内网地址，均可用对应环境变量覆盖
    return Settings(
        videoai_base_url=_env("VIDEOAI_BACKEND_URL", "http://localhost:8081").rstrip("/"),
        videoai_media_base_url=(
            _env("VIDEOAI_MEDIA_BACKEND_URL", "") or _env("VIDEOAI_BACKEND_URL", "http://localhost:8081")
        ).rstrip("/"),
        person_api_base_url=_env("PERSON_API_BASE_URL", "http://192.168.11.192:18890").rstrip("/"),
        retrieve_api_base_url=_env("RETRIEVE_API_BASE_URL", "http://192.168.11.194:15011").rstrip("/"),
        retrieve_api_timeout_seconds=float(_env("RETRIEVE_API_TIMEOUT_SECONDS", "120")),
        video_understanding_api_base_url=_env("VIDEO_UNDERSTANDING_API_BASE_URL", "http://192.168.11.192:8775").rstrip("/"),
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
        hcnetsdk_download_nvr_hosts=_env_csv(
            "HCNETSDK_DOWNLOAD_NVR_HOSTS",
            "10.10.7.252,10.10.7.253",
        ),
        hcnetsdk_download_port=_env_int("HCNETSDK_DOWNLOAD_PORT", 8000),
        hcnetsdk_download_username=_env("HCNETSDK_DOWNLOAD_USERNAME", "admin"),
        hcnetsdk_download_password=_env("HCNETSDK_DOWNLOAD_PASSWORD", ""),
        hcnetsdk_download_channel=_env_int("HCNETSDK_DOWNLOAD_CHANNEL", 1),
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
        # 录像动态链接（/recording-live）对外暴露的 MCP 访问基址
        mcp_public_base_url=_env("VIDEOAI_MCP_PUBLIC_BASE_URL", "http://192.168.11.194:8097").rstrip("/"),
        camera_import_username=_env("CAMERA_IMPORT_USERNAME", ""),
        # 口令不做 strip，保持与原 CLI 读取语义一致
        camera_import_password=os.getenv("CAMERA_IMPORT_PASSWORD", ""),
        camera_import_backend_url=(
            _env("VIDEOAI_MEDIA_BACKEND_URL", "") or _env("VIDEOAI_BACKEND_URL", "http://backend:8081")
        ).rstrip("/"),
    )
