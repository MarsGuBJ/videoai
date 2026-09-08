"""以图搜人 / 文本检索代理与查询图片资源路由。"""

from urllib.parse import quote

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.schemas.person_search import (
    PersonSearchByBboxRequest,
    PersonSearchDetectRequest,
    PersonSearchImageResponse,
    TextSearchQueryRequest,
)
from app.services.person_search import person_api_get, person_api_post, required_text, retrieve_api_post
from app.services.search_keywords import SEARCH_TYPE_TEXT_IMAGE, record_search_keyword
from app.utils.assets import save_query_image

TEXT_SEARCH_DEFAULT_PAGE = 1
TEXT_SEARCH_DEFAULT_PAGE_SIZE = 10
TEXT_SEARCH_MAX_PAGE_SIZE = 100
DEFAULT_SEARCH_TOP_K = 10
DEFAULT_SEARCH_METHOD = "reid"

router = APIRouter()


@router.post("/api/person-search/images", response_model=PersonSearchImageResponse)
async def upload_person_search_image(
    request: Request,
    image: UploadFile = File(...),  # noqa: B008  # FastAPI File 依赖注入惯例
) -> PersonSearchImageResponse:
    """上传查询图片，返回可对外访问的 URL 与路径。"""
    image_path = await save_query_image(image)
    public_path = f"/api/assets/query-images/{image_path.name}"
    public_base = get_settings().backend_public_url or str(request.base_url).rstrip("/")
    return PersonSearchImageResponse(
        imageUrl=f"{public_base}{public_path}",
        imagePath=public_path,
    )


@router.get("/api/assets/query-images/{filename}")
def query_image_asset(filename: str) -> FileResponse:
    """返回查询图片文件（带目录穿越防护）。"""
    query_image_storage_dir = get_settings().query_image_storage_dir
    path = (query_image_storage_dir / filename).resolve()
    if not str(path).startswith(str(query_image_storage_dir.resolve())) or not path.is_file():
        raise HTTPException(status_code=404, detail="Query image not found")
    return FileResponse(path)


@router.post("/api/person-search/detect-persons")
def detect_persons_proxy(request: PersonSearchDetectRequest) -> dict:
    """代理：检测图片中的人形目标。"""
    return person_api_post(
        "/vlm-application/search/detectPersons",
        {"image_url": required_text(request.imageUrl, "imageUrl")},
    )


@router.post("/api/person-search/search-by-bbox")
def search_person_by_bbox_proxy(request: PersonSearchByBboxRequest) -> dict:
    """代理：按 bbox 以图搜人。"""
    payload = {
        "image_url": required_text(request.imageUrl, "imageUrl"),
        "search_method": request.searchMethod or DEFAULT_SEARCH_METHOD,
        "similarity_threshold": request.similarityThreshold,
        "top_k": max(1, int(request.topK or DEFAULT_SEARCH_TOP_K)),
    }
    if request.bbox:
        payload["bbox"] = request.bbox
    if request.startTime:
        payload["start_time"] = request.startTime
    if request.endTime:
        payload["end_time"] = request.endTime
    return person_api_post("/vlm-application/search/searchPersonByBbox", payload)


@router.get("/api/person-search/results/{task_id}")
def person_search_result_proxy(task_id: str) -> dict:
    """代理：轮询以图搜人任务结果。"""
    safe_task_id = required_text(task_id, "taskId")
    return person_api_get(f"/vlm-application/search/searchPersonResult/{quote(safe_task_id, safe='')}")


@router.post("/api/text-search/query")
def text_search_query_proxy(request: TextSearchQueryRequest) -> dict:
    """代理：自然语言视频检索（文搜图）；记录关键词用于统计。"""
    message = required_text(request.message, "message")
    record_search_keyword(message, SEARCH_TYPE_TEXT_IMAGE)
    payload = {
        "message": message,
        "start_time": request.startTime or None,
        "end_time": request.endTime or None,
        "location": request.location or None,
        "page": max(1, int(request.page or TEXT_SEARCH_DEFAULT_PAGE)),
        "page_size": max(1, min(int(request.pageSize or TEXT_SEARCH_DEFAULT_PAGE_SIZE), TEXT_SEARCH_MAX_PAGE_SIZE)),
    }
    return retrieve_api_post("/v1/retrieve/query", payload)
