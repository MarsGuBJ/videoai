"""复核任务 CRUD 与大模型判定路由。"""

import threading
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app import state
from app.core.config import get_settings
from app.schemas.review_task import ReviewTaskOut
from app.services.review_tasks import (
    delete_review_task_from_db,
    persist_review_task,
    require_review_task,
    review_task_out,
    run_review_task_judgment,
)
from app.services.review_types import require_review_type
from app.utils.assets import asset_path, save_review_image

router = APIRouter()


@router.get("/api/review-tasks", response_model=list[ReviewTaskOut])
def list_review_tasks() -> list[ReviewTaskOut]:
    """按创建时间倒序返回全部复核任务。"""
    records = sorted(state.review_tasks_store.values(), key=lambda item: item["created_at"], reverse=True)
    return [review_task_out(record) for record in records]


@router.post("/api/review-tasks", response_model=ReviewTaskOut)
async def create_review_task(
    review_type_id: str = Form(..., alias="reviewTypeId"),  # noqa: B008  # FastAPI Form 依赖注入惯例
    llm_config_id: str = Form(..., alias="llmConfigId"),  # noqa: B008  # FastAPI Form 依赖注入惯例
    image: UploadFile = File(...),  # noqa: B008  # FastAPI File 依赖注入惯例
) -> ReviewTaskOut:
    """创建复核任务：校验复核类型与大模型配置，存图入内存并落库，后台线程执行大模型判定。"""
    review_type = require_review_type(review_type_id)
    llm_cfg = state.llm_configs_store.get(llm_config_id)
    if not llm_cfg:
        raise HTTPException(status_code=404, detail="LLM config not found")
    image_bytes = await image.read()
    await image.seek(0)
    image_url = await save_review_image(image)
    task_id = str(uuid4())
    now = datetime.now(timezone.utc)
    record = {
        "id": task_id,
        "review_type_id": review_type_id,
        "review_type_name": str(review_type["name"]),
        "review_type_code": str(review_type["code"]),
        "llm_config_id": llm_config_id,
        "llm_config_name": str(llm_cfg["name"]),
        "image_url": image_url,
        "status": "进行中",
        "verdict": "",
        "reason": "",
        "created_at": now,
        "updated_at": now,
    }
    state.review_tasks_store[task_id] = record
    persist_review_task(record)
    threading.Thread(target=run_review_task_judgment, args=(task_id, image_bytes), daemon=True).start()
    return review_task_out(record)


@router.get("/api/review-tasks/{task_id}", response_model=ReviewTaskOut)
def get_review_task(task_id: str) -> ReviewTaskOut:
    """按 ID 返回复核任务（含最新判定状态）。"""
    return review_task_out(require_review_task(task_id))


@router.delete("/api/review-tasks/{task_id}")
def delete_review_task(task_id: str) -> dict[str, str]:
    """删除复核任务：移出内存并删库。"""
    record = state.review_tasks_store.pop(task_id, None)
    if not record:
        raise HTTPException(status_code=404, detail="Review task not found")
    delete_review_task_from_db(task_id)
    return {"deleted": task_id}


@router.get("/api/assets/review-images/{filename}")
def review_image_asset(filename: str) -> FileResponse:
    """返回复核任务图片文件（带目录穿越防护）。"""
    review_image_storage_dir = get_settings().review_image_storage_dir
    path = asset_path(f"/api/assets/review-images/{filename}", review_image_storage_dir)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="Review image not found")
    return FileResponse(path)
