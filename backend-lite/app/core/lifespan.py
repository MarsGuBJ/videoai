"""应用生命周期：替代原 @app.on_event 的 startup/shutdown 逻辑。

启动顺序与原逻辑逐一对应：建表与轻量迁移（容错）→ 载入布控任务 →
载入人脸档案/向量 → 模型注册表种子 → 摄像头缓存 → worker 流对齐 →
人脸种子 → worker 守护线程 →（可选）人脸扫描线程；关闭时反向清理。
"""

import logging
import threading
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError

from app import state
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.services import camera_cache
from app.services.algorithms import load_algorithms_from_db
from app.services.deployment_tasks import ensure_deployment_task_schema, load_deployment_tasks_from_db
from app.services.event_dedup_rules import ensure_dedup_rule_schema, load_dedup_rules_from_db
from app.services.event_infos import ensure_event_info_schema, load_event_infos_from_db
from app.services.event_push_tasks import ensure_push_task_schema, load_push_tasks_from_db
from app.services.events import ensure_deployment_event_schema, migrate_face_match_events
from app.services.face_scan import face_scan_loop
from app.services.faces import load_face_embeddings, load_faces_from_disk
from app.services.llm_configs import ensure_llm_config_schema, load_llm_configs_from_db
from app.services.review_schedules import (
    ensure_review_schedule_schema,
    load_review_schedules_from_db,
    review_schedule_loop,
)
from app.services.review_tasks import ensure_review_task_schema, load_review_tasks_from_db
from app.services.review_types import ensure_review_type_schema, load_review_types_from_db
from app.services.search_keywords import ensure_search_keyword_schema, load_search_keywords_from_db
from app.services.seed import seed_face_profiles, seed_model_registry
from app.services.worker_nodes import ensure_worker_node_schema, load_worker_nodes_from_db
from app.services.worker_streams import ensure_worker_streams, worker_stream_guard_loop

logger = logging.getLogger(__name__)

THREAD_JOIN_TIMEOUT_SECONDS = 2


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI lifespan：完成全部启动初始化与关闭清理。"""
    settings = get_settings()

    settings.face_storage_dir.mkdir(parents=True, exist_ok=True)
    settings.snapshot_storage_dir.mkdir(parents=True, exist_ok=True)
    settings.query_image_storage_dir.mkdir(parents=True, exist_ok=True)
    settings.review_image_storage_dir.mkdir(parents=True, exist_ok=True)
    settings.storage_algorithm_dir.mkdir(parents=True, exist_ok=True)

    try:
        Base.metadata.create_all(engine)
        ensure_deployment_task_schema()
        ensure_deployment_event_schema()
        ensure_llm_config_schema()
        ensure_review_type_schema()
        ensure_review_task_schema()
        ensure_review_schedule_schema()
        ensure_event_info_schema()
        ensure_dedup_rule_schema()
        ensure_push_task_schema()
        ensure_worker_node_schema()
        ensure_search_keyword_schema()
    except SQLAlchemyError as exc:  # 数据库不可达时服务仍需可启动（与原逻辑一致）
        logger.error("Base.metadata.create_all failed: %s", exc)

    migrate_face_match_events()

    load_deployment_tasks_from_db()
    load_algorithms_from_db()
    load_llm_configs_from_db()
    load_review_types_from_db()
    load_review_tasks_from_db()
    load_review_schedules_from_db()
    load_event_infos_from_db()
    load_dedup_rules_from_db()
    load_push_tasks_from_db()
    load_worker_nodes_from_db()
    load_search_keywords_from_db()
    load_faces_from_disk()
    load_face_embeddings()
    seed_model_registry()
    camera_cache.start()
    ensure_worker_streams()
    seed_face_profiles()

    state.worker_guard_stop_event.clear()
    state.worker_guard_thread = threading.Thread(target=worker_stream_guard_loop, daemon=True)
    state.worker_guard_thread.start()

    state.review_scheduler_stop_event.clear()
    state.review_scheduler_thread = threading.Thread(
        target=review_schedule_loop, args=(state.review_scheduler_stop_event,), daemon=True
    )
    state.review_scheduler_thread.start()

    if settings.face_scan_enabled:
        state.scanner_stop_event.clear()
        state.scanner_thread = threading.Thread(target=face_scan_loop, daemon=True)
        state.scanner_thread.start()

    yield

    state.scanner_stop_event.set()
    if state.scanner_thread and state.scanner_thread.is_alive():
        state.scanner_thread.join(timeout=THREAD_JOIN_TIMEOUT_SECONDS)
    state.worker_guard_stop_event.set()
    if state.worker_guard_thread and state.worker_guard_thread.is_alive():
        state.worker_guard_thread.join(timeout=THREAD_JOIN_TIMEOUT_SECONDS)
    state.review_scheduler_stop_event.set()
    if state.review_scheduler_thread and state.review_scheduler_thread.is_alive():
        state.review_scheduler_thread.join(timeout=THREAD_JOIN_TIMEOUT_SECONDS)
    camera_cache.stop()
