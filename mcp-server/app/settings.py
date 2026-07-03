from dataclasses import dataclass
import os


def _env(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


@dataclass(frozen=True)
class Settings:
    videoai_base_url: str
    zlm_http_url: str
    zlm_public_http_url: str
    zlm_secret: str
    zlm_rtmp_push_base: str
    hikvision_base_url: str
    hikvision_username: str
    hikvision_password: str
    playback_ttl_seconds: int
    request_timeout_seconds: float
    mcp_host: str
    mcp_port: int
    mcp_transport: str


def load_settings() -> Settings:
    return Settings(
        videoai_base_url=_env("VIDEOAI_BACKEND_URL", "http://localhost:8081").rstrip("/"),
        zlm_http_url=_env("VIDEOAI_ZLM_HTTP_URL", "http://127.0.0.1:8082").rstrip("/"),
        zlm_public_http_url=_env("VIDEOAI_ZLM_PUBLIC_HTTP_URL", "http://192.168.11.194:9100").rstrip("/"),
        zlm_secret=_env("VIDEOAI_ZLM_SECRET", "TFtkiHhkoFJzgamQXuYY1zACl2XYSnUR"),
        zlm_rtmp_push_base=_env("VIDEOAI_ZLM_RTMP_PUSH_BASE", "rtmp://127.0.0.1:1945/live").rstrip("/"),
        hikvision_base_url=_env("HIKVISION_NVR_BASE_URL", "").rstrip("/"),
        hikvision_username=_env("HIKVISION_NVR_USERNAME", ""),
        hikvision_password=_env("HIKVISION_NVR_PASSWORD", ""),
        playback_ttl_seconds=_env_int("VIDEOAI_MCP_PLAYBACK_TTL_SECONDS", 300),
        request_timeout_seconds=float(_env("VIDEOAI_MCP_REQUEST_TIMEOUT_SECONDS", "15")),
        mcp_host=_env("VIDEOAI_MCP_HOST", "0.0.0.0"),
        mcp_port=_env_int("VIDEOAI_MCP_PORT", 8091),
        mcp_transport=_env("VIDEOAI_MCP_TRANSPORT", "streamable-http"),
    )
