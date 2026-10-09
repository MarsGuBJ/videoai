"""FastAPI 应用装配：create_app()、中间件、异常处理、路由与前端静态资源。"""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routers import (
    algorithms,
    deployment_tasks,
    event_dedup_rules,
    event_infos,
    event_push_tasks,
    events,
    face_library,
    faces,
    health,
    internal,
    llm_configs,
    models,
    open_llm_configs,
    person_search,
    recordings,
    review_schedules,
    review_tasks,
    review_types,
    search_keywords,
    storage_bindings,
    video_analysis,
    windows_camera,
    worker_nodes,
)
from app.core.config import PROJECT_ROOT
from app.core.exceptions import AppError
from app.core.lifespan import lifespan
from app.core.logging import setup_logging
from app.core.trace import TraceIdMiddleware, current_trace_id

logger = logging.getLogger(__name__)

FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

_ROUTERS = (
    health.router,
    algorithms.router,
    deployment_tasks.router,
    faces.router,
    face_library.router,
    person_search.router,
    video_analysis.router,
    recordings.router,
    events.router,
    internal.router,
    models.router,
    windows_camera.router,
    llm_configs.router,
    open_llm_configs.router,
    review_tasks.router,
    review_schedules.router,
    review_types.router,
    search_keywords.router,
    storage_bindings.router,
    event_infos.router,
    event_dedup_rules.router,
    event_push_tasks.router,
    worker_nodes.router,
)

_TAG_NAMES = (
    "健康检查",
    "算法",
    "部署任务",
    "人脸",
    "人脸库",
    "人员检索",
    "视频分析",
    "录像回放",
    "事件",
    "内部接口",
    "模型",
    "Windows 摄像头",
    "大模型配置",
    "开放大模型配置",
    "复核任务",
    "复核计划",
    "复核类型",
    "检索关键词",
    "录像存储绑定",
    "事件信息",
    "事件去重规则",
    "事件推送任务",
    "Worker 节点",
)

async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    """把 AppError 转为 {code, message, traceId}（仅新增字段，不改既有契约）。

    Args:
        _request: 当前请求（未使用）。
        exc: 应用异常。

    Returns:
        带错误码与 traceId 的 JSON 响应。
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "traceId": current_trace_id()},
    )


def create_app() -> FastAPI:
    """装配并返回 FastAPI 应用实例。

    Returns:
        完成中间件、异常处理与路由注册的 app。
    """
    setup_logging()
    app = FastAPI(
        title="VideoAI Lite Backend",
        description="视觉大模型平台轻量后端 API",
        version="0.1.0",
        openapi_tags=[{"name": name} for name in _TAG_NAMES],
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TraceIdMiddleware)
    app.add_exception_handler(AppError, app_error_handler)

    for router in _ROUTERS:
        app.include_router(router)

    if FRONTEND_DIST.is_dir():
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="frontend_assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_frontend(full_path: str) -> FileResponse:
            """SPA 兜底路由：非 /api 路径一律回退到 index.html。"""
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="Not Found")
            index_path = FRONTEND_DIST / "index.html"
            if index_path.is_file():
                return FileResponse(index_path)
            raise HTTPException(status_code=404, detail="Frontend not built")

    return app


app = create_app()
