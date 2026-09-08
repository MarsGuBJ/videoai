"""集中式配置：全部环境变量在此定义，业务代码一律经 get_settings() 读取。

默认值语义与重构前完全一致（含内网 IP 默认值，见 .env.example 注释）；
仅做收敛，不做行为调整。
"""

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """backend-lite 全部运行时配置。

    字段名为 snake_case，通过 validation_alias 或默认的大小写不敏感
    环境变量名映射到 env；带 VIDEOAI_ 前缀的别名优先于历史无名前缀变量。
    """

    model_config = SettingsConfigDict(extra="ignore")

    # 流媒体 / Worker
    srs_http_url: str = Field(
        default="http://localhost:8080",
        validation_alias=AliasChoices("VIDEOAI_ZLM_HTTP_URL", "SRS_HTTP_URL"),
    )
    worker_url: str = Field(
        default="http://localhost:8090",
        validation_alias=AliasChoices("VIDEOAI_WORKER_URL", "WORKER_URL"),
    )
    ffmpeg_bin: str = "ffmpeg"
    dino_camera_hosts: str = Field(default="192.168.11.65", validation_alias="VIDEOAI_DINO_CAMERA_HOSTS")

    # Windows 摄像头（WSL 场景）
    windows_ffmpeg_bin: str = "ffmpeg"
    windows_camera_name: str = "Surface Camera Front"
    windows_camera_stream: str = "win_camera"

    # 存储目录
    face_storage_dir: Path = Field(
        default=PROJECT_ROOT / "storage" / "faces",
        validation_alias="VIDEOAI_STORAGE_FACE_DIR",
    )
    snapshot_storage_dir: Path = Field(
        default=PROJECT_ROOT / "storage" / "snapshots",
        validation_alias="VIDEOAI_STORAGE_SNAPSHOT_DIR",
    )
    query_image_storage_dir: Path = Field(
        default=PROJECT_ROOT / "storage" / "query-images",
        validation_alias="VIDEOAI_STORAGE_QUERY_IMAGE_DIR",
    )
    review_image_storage_dir: Path = Field(
        default=PROJECT_ROOT / "storage" / "review-images",
        validation_alias="VIDEOAI_STORAGE_REVIEW_IMAGE_DIR",
    )
    storage_algorithm_dir: Path = Field(
        default=PROJECT_ROOT / "storage" / "algorithms",
        validation_alias="VIDEOAI_STORAGE_ALGORITHM_DIR",
    )

    # 外部检索服务（内网默认值为历史约定，见 .env.example）
    person_api_base_url: str = "http://192.168.11.192:18890"
    retrieve_api_base_url: str = "http://192.168.11.194:15011"
    video_analysis_api_base_url: str = "http://192.168.11.192:8775"
    mcp_server_base_url: str = "http://192.168.11.194:8097"
    # MinIO（文搜视频：本地视频上传后供分析服务拉取；默认值与 mcp-server 侧一致）
    minio_endpoint: str = Field(default="192.168.11.194", validation_alias="MINIO_ENDPOINT")
    minio_port: int = Field(default=9000, validation_alias="MINIO_PORT")
    minio_use_ssl: bool = Field(default=False, validation_alias="MINIO_USE_SSL")
    minio_access_key: str = Field(default="minio", validation_alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="Klg4dM9F3H", validation_alias="MINIO_SECRET_KEY")  # noqa: S105  # 与 mcp-server 侧默认值一致，生产经 env 覆盖
    minio_bucket: str = Field(default="public", validation_alias="MINIO_BUCKET")
    backend_public_url: str = Field(
        default="",
        validation_alias=AliasChoices("VIDEOAI_BACKEND_PUBLIC_URL", "BACKEND_PUBLIC_URL"),
    )

    # 人脸扫描
    face_scan_enabled: bool = False
    face_scan_interval_seconds: int = 300
    face_scan_initial_delay_seconds: int = 10
    face_scan_timeout_seconds: int = 15
    face_match_threshold: float = 0.45
    face_event_cooldown_seconds: int = 60

    # Worker 节点监控：超过该秒数未收到心跳视为离线
    worker_node_offline_seconds: int = 30

    # Triton 模型服务
    triton_http_url: str = "http://localhost:8000"
    triton_model_repository: Path = PROJECT_ROOT / "infra" / "model_repository"

    # 摄像头缓存（Java media backend）
    media_backend_url: str = Field(default="http://localhost:8082", validation_alias="VIDEOAI_MEDIA_BACKEND_URL")
    camera_cache_refresh_interval_seconds: float = Field(
        default=10.0,
        validation_alias="VIDEOAI_CAMERA_CACHE_REFRESH_INTERVAL_SECONDS",
    )
    camera_cache_timeout_seconds: float = Field(
        default=5.0,
        validation_alias="VIDEOAI_CAMERA_CACHE_TIMEOUT_SECONDS",
    )

    # 数据库
    videoai_database_url: str | None = Field(default=None, validation_alias="VIDEOAI_DATABASE_URL")
    postgres_host: str = "postgres"
    postgres_port: str = "5432"
    postgres_user: str = "videoai"
    postgres_password: str = "videoai"  # noqa: S105  # 本地开发默认口令，与重构前一致，生产经 env 覆盖
    postgres_db: str = "videoai"

    # 日志
    log_json: bool = False
    log_format: str | None = None

    @field_validator("face_scan_enabled", mode="before")
    @classmethod
    def _parse_face_scan_enabled(cls, value: object) -> bool:
        """保持原语义：除字符串 "false"（忽略大小写）外一律视为开启。"""
        if isinstance(value, bool):
            return value
        return str(value).lower() != "false"

    @field_validator("srs_http_url", "worker_url", "triton_http_url", "media_backend_url")
    @classmethod
    def _rstrip_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator(
        "person_api_base_url",
        "retrieve_api_base_url",
        "video_analysis_api_base_url",
        "mcp_server_base_url",
        "backend_public_url",
    )
    @classmethod
    def _strip_and_rstrip(cls, value: str) -> str:
        return value.strip().rstrip("/")

    @property
    def dino_camera_host_set(self) -> set[str]:
        """DINO 目标检测摄像头主机集合（逗号分隔 env 的解析结果）。"""
        return {item.strip() for item in self.dino_camera_hosts.split(",") if item.strip()}

    @property
    def face_metadata_file(self) -> Path:
        return self.face_storage_dir / "faces.json"

    @property
    def face_embeddings_file(self) -> Path:
        return self.face_storage_dir / "face_embeddings.json"

    @property
    def database_url(self) -> str:
        """显式 VIDEOAI_DATABASE_URL 优先，否则按 POSTGRES_* 拼装。"""
        if self.videoai_database_url:
            return self.videoai_database_url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """返回进程级单例 Settings（env 在首次调用时读取一次）。"""
    return Settings()
