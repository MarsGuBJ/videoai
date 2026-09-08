"""Runtime assembly: settings, the FastMCP instance and shared backend clients."""

from datetime import timedelta, timezone

from mcp.server.fastmcp import FastMCP

from .hcnetsdk_playback import HcNetSdkPlaybackProxy
from .hikvision_nvr import HikvisionNvrClient
from .media_proxy import MediaProxy
from .minio_storage import RecordingMp4Storage
from .nvr_devices import NvrChannelLookup, NvrDeviceRegistry
from .person_api_client import PersonApiClient
from .recording_cache import RecordingCache
from .retrieve_api_client import RetrieveApiClient
from .settings import load_settings
from .video_analysis_client import VideoAnalysisClient
from .videoai_client import VideoAiClient

settings = load_settings()

mcp = FastMCP(
    "videoai-monitoring",
    instructions="Query VideoAI cameras and create live or Hikvision NVR recording playback URLs.",
    host=settings.mcp_host,
    port=settings.mcp_port,
    streamable_http_path="/mcp",
    sse_path="/sse",
)

videoai = VideoAiClient(
    settings.videoai_base_url,
    settings.request_timeout_seconds,
    media_base_url=settings.videoai_media_base_url,
)
person_api = PersonApiClient(settings.person_api_base_url, settings.request_timeout_seconds)
retrieve_api = RetrieveApiClient(settings.retrieve_api_base_url, settings.retrieve_api_timeout_seconds)
video_analysis = VideoAnalysisClient(settings.video_analysis_api_base_url, settings.video_analysis_timeout_seconds)
hikvision = HikvisionNvrClient(
    settings.hikvision_base_url,
    settings.hikvision_username,
    settings.hikvision_password,
    settings.request_timeout_seconds,
)
media_proxy = MediaProxy(
    settings.zlm_http_url,
    settings.zlm_public_http_url,
    settings.zlm_secret,
    settings.zlm_rtmp_push_base,
    settings.playback_ttl_seconds,
    settings.request_timeout_seconds,
)
hcnetsdk_playback = HcNetSdkPlaybackProxy(
    settings.hcnetsdk_host,
    settings.hcnetsdk_port,
    settings.hcnetsdk_username,
    settings.hcnetsdk_password,
    settings.hcnetsdk_channel,
    settings.zlm_http_url,
    settings.zlm_public_http_url,
    settings.zlm_secret,
    settings.zlm_rtmp_push_base,
    settings.playback_ttl_seconds,
    settings.request_timeout_seconds,
)
# 按摄像头绑定的多 NVR 设备回放代理注册表（凭据来自摄像头 sourceUrl，按设备主机缓存）
nvr_devices = NvrDeviceRegistry(
    settings.zlm_http_url,
    settings.zlm_public_http_url,
    settings.zlm_secret,
    settings.zlm_rtmp_push_base,
    settings.playback_ttl_seconds,
    settings.request_timeout_seconds,
)
# 已知 NVR 主机集合：摄像头 sourceUrl 指向它们时按 NVR 直连解析；否则视为直连 IPC，
# 通过 channel_lookup 反查其所属 NVR 与通道（平台 nvrTrackId 对直连 IPC 可能是脏数据）
known_nvr_hosts = frozenset({settings.hcnetsdk_host, *settings.hcnetsdk_download_nvr_hosts})
channel_lookup = NvrChannelLookup(
    settings.hcnetsdk_download_nvr_hosts,
    settings.hcnetsdk_download_username,
    settings.hcnetsdk_download_password,
    settings.request_timeout_seconds,
)
hcnetsdk_downloaders = {
    host: HcNetSdkPlaybackProxy(
        host,
        settings.hcnetsdk_download_port,
        settings.hcnetsdk_download_username,
        settings.hcnetsdk_download_password,
        settings.hcnetsdk_download_channel,
        settings.zlm_http_url,
        settings.zlm_public_http_url,
        settings.zlm_secret,
        settings.zlm_rtmp_push_base,
        settings.playback_ttl_seconds,
        settings.request_timeout_seconds,
    )
    for host in settings.hcnetsdk_download_nvr_hosts
}
recording_mp4_storage = RecordingMp4Storage(
    settings.minio_endpoint,
    settings.minio_port,
    settings.minio_use_ssl,
    settings.minio_access_key,
    settings.minio_secret_key,
    settings.minio_bucket,
)
recording_cache = RecordingCache(settings.playback_ttl_seconds)
DEFAULT_RECORDING_RESULT_LIMIT = 50
SEARCH_RECORDINGS_RESULT_LIMIT = 1
DEFAULT_RECORDING_TRACK_ID = "601"
DEFAULT_RECORDING_TIMEZONE = timezone(timedelta(hours=8))
RECORDING_OVERLAY_TEXT = ""
DINO_EVENT_SOURCE = "视觉平台"
DINO_EVENT_TYPE = "DINO Object Detection"
DINO_EVENT_STATUS = "有效"
DINO_EVENT_LEVEL = 1
DINO_EVENT_COUNT = 10
DINO_DEFAULT_CAMERA_NAMES = (
    "摄像头101",
    "摄像头102",
    "摄像头103",
    "摄像头104",
    "摄像头105",
)
