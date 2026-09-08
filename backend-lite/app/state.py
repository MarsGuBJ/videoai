"""进程内共享状态（原 main.py 全局变量的集中地）。

只存放容器与线程句柄，不含业务逻辑；services 与 routers 共同读写，
以此避免模块间循环依赖。
"""

import queue
import subprocess
import threading
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.schemas import (
    DeploymentTaskResponse,
    FaceEventResponse,
    FaceProfileResponse,
    ModelResponse,
    ObjectEventResponse,
)
from app.schemas.algorithm import AlgorithmRecord

_settings = get_settings()

faces_store: dict[UUID, FaceProfileResponse] = {}
face_embeddings: dict[UUID, list[float]] = {}
events_store: list[FaceEventResponse] = []
object_events_store: list[ObjectEventResponse] = []
deployment_tasks_store: dict[UUID, DeploymentTaskResponse] = {}
algorithms_store: dict[UUID, AlgorithmRecord] = {}
llm_configs_store: dict[str, dict[str, Any]] = {}
review_types_store: dict[str, dict[str, Any]] = {}
review_tasks_store: dict[str, dict[str, Any]] = {}
review_schedules_store: dict[str, dict[str, Any]] = {}
worker_nodes_store: dict[str, dict[str, Any]] = {}
event_infos_store: dict[str, dict[str, Any]] = {}
event_dedup_rules_store: dict[str, dict[str, Any]] = {}
event_push_tasks_store: dict[str, dict[str, Any]] = {}
search_keywords_store: list[dict[str, Any]] = []
object_event_cooldowns: dict[str, float] = {}
event_subscribers: list[queue.Queue[str]] = []
event_lock = threading.Lock()

# 人脸扫描后台线程
scanner_stop_event = threading.Event()
scanner_thread: threading.Thread | None = None

# worker 流 reconcile 守护线程
worker_guard_stop_event = threading.Event()
worker_guard_thread: threading.Thread | None = None

# 定时复核调度线程
review_scheduler_stop_event = threading.Event()
review_scheduler_thread: threading.Thread | None = None

# Windows 摄像头推流子进程
windows_camera_process: subprocess.Popen[bytes] | None = None
windows_camera_device: str = _settings.windows_camera_name
windows_camera_stream: str = _settings.windows_camera_stream

# Triton 模型注册表
model_registry: dict[str, ModelResponse] = {}
