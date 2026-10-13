"""以图搜人 / 文本检索代理与查询图片资源路由。"""

import logging
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
from app.services.minio_files import rewrite_minio_media_fields
from app.services.person_search import (
    absolutize_image_url,
    es_document_api_post,
    person_api_get,
    person_api_post,
    person_search_submit,
    required_text,
    retrieve_api_post,
)
from app.services.search_keywords import SEARCH_TYPE_TEXT_IMAGE, record_search_keyword
from app.utils.assets import save_query_image

logger = logging.getLogger(__name__)

TEXT_SEARCH_DEFAULT_PAGE = 1
TEXT_SEARCH_DEFAULT_PAGE_SIZE = 10
TEXT_SEARCH_MAX_PAGE_SIZE = 100
DEFAULT_SEARCH_TOP_K = 10
DEFAULT_SEARCH_METHOD = "reid"

router = APIRouter(tags=["人员检索"])


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
    """代理：检测图片中的人形目标。

    imageUrl 允许传后端自身的相对资源路径（文搜视频页签传的是 /api/... 截图地址），
    转发前补全为公网绝对地址，否则外部服务会把它当 base64 解析并报错。
    """
    return person_api_post(
        "/vlm-application/search/detectPersons",
        {"image_url": absolutize_image_url(required_text(request.imageUrl, "imageUrl"))},
    )


@router.post("/api/person-search/search-by-bbox")
def search_person_by_bbox_proxy(request: PersonSearchByBboxRequest) -> dict:
    """代理：按 bbox 以图搜人；imageUrl 处理同 detect-persons。

    2026-09 上游重构：优先调详版 `searchPersonFull`
    （上游直接返回 ES 全量文档组成的 similar_persons，无需再依赖 ES 文档查询接口）；
    旧版上游镜像（无 searchPersonFull 路由）由 person_search_submit 自动回退
    `searchPersonByBbox`，简版 es_ids 结果由 resolve_similar_persons 兜底补齐。
    """
    payload = {
        "image_url": absolutize_image_url(required_text(request.imageUrl, "imageUrl")),
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
    # 服务端属性筛选（性别/年龄段/上衣颜色），上游字段为 sex/age/top_color
    if request.sex:
        payload["sex"] = request.sex
    if request.age:
        payload["age"] = request.age
    if request.topColor:
        payload["top_color"] = request.topColor
    return person_search_submit(payload)


@router.get("/api/person-search/results/{task_id}")
def person_search_result_proxy(task_id: str) -> dict:
    """代理：轮询以图搜人任务结果；result 中只有 es_ids 时经 ES 文档接口解析为完整人员文档。"""
    safe_task_id = required_text(task_id, "taskId")
    response = person_api_get(f"/vlm-application/search/searchPersonResult/{quote(safe_task_id, safe='')}")
    return resolve_similar_persons(response)


def resolve_similar_persons(response: dict) -> dict:
    """把任务结果里的 es_ids 解析为 similar_persons（前端结果卡片期望的结构）。

    详版 `searchPersonFull` 已在 `data.data.result.similar_persons` 直接返回 ES 全量文档，
    此时原样透传；仅当上游按简版 `searchPersonBrief` 只回 es_ids + index_name 时，
    才调用检索配套服务的 es-documents/by-ids 补齐文档字段。解析失败时透传原始响应，
    不影响任务状态轮询。两种来源的文档都会把 MinIO 媒体地址（image_url/video_url 等）
    改写为同源代理路径，避免浏览器直连 MinIO 被现场链路限速（见 services.minio_files）；
    上游偶发返回不带图片地址的文档（前端会渲染成裂图卡片），这类条目对展示无意义，直接丢弃。
    """
    result = ((response.get("data") or {}).get("data") or {}).get("result")
    if not isinstance(result, dict):
        return response
    similar_persons = result.get("similar_persons")
    if similar_persons:
        result["similar_persons"] = _normalize_person_entries(similar_persons)
        return response
    resolved = _similar_persons_from_es_ids(result)
    if resolved:
        result["similar_persons"] = _normalize_person_entries(resolved)
    return response


def _normalize_person_entries(persons: list) -> list[dict]:
    """改写条目里的 MinIO 媒体地址，并丢弃无图片地址的条目（上游偶发的残缺文档）。"""
    normalized = []
    for entry in persons:
        if not isinstance(entry, dict):
            continue
        rewrite_minio_media_fields(entry)
        if str(entry.get("image_url") or "").strip():
            normalized.append(entry)
    return normalized


def _similar_persons_from_es_ids(result: dict) -> list[dict]:
    """简版结果（es_ids + index_name）经 es-documents/by-ids 补齐为完整人员文档。"""
    result_data = result.get("data")
    es_ids = result_data.get("es_ids") if isinstance(result_data, dict) else None
    if not es_ids:
        return []
    try:
        documents = es_document_api_post("/api/v1/queries/es-documents/by-ids", {"esids": es_ids})
    except HTTPException:
        logger.warning("es-documents/by-ids 解析失败，透传 es_ids 原始结果", exc_info=True)
        return []
    items = documents.get("items") or []
    similar_persons = []
    for item in items:
        if not isinstance(item, dict):
            continue
        payload = item.get("payload")
        if not isinstance(payload, dict):
            continue
        entry = dict(payload)
        entry["es_doc_id"] = item.get("document_id")
        if item.get("score") is not None:
            entry.setdefault("similarity_score", item.get("score"))
        similar_persons.append(entry)
    # by-ids 不保证按入参顺序返回，按 es_ids 顺序重排（相似度由高到低）
    order = {doc_id: index for index, doc_id in enumerate(es_ids)}
    similar_persons.sort(key=lambda entry: order.get(entry.get("es_doc_id"), len(order)))
    return similar_persons


@router.post("/api/text-search/query")
def text_search_query_proxy(request: TextSearchQueryRequest) -> dict:
    """代理：自然语言视频检索（文搜图）；记录关键词用于统计。

    结果条目里的 MinIO 媒体地址（image_url/video_url 等）改写为同源代理路径，
    避免浏览器直连 MinIO 被现场链路限速（与以图搜人结果同一处理）。
    """
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
    if request.searchMode:
        payload["search_mode"] = request.searchMode
    if request.confidence is not None:
        payload["confidence"] = request.confidence
    if request.sortOrder:
        payload["sort_order"] = request.sortOrder
    response = retrieve_api_post("/v1/retrieve/query", payload)
    data = response.get("data")
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        return response
    kept_items = []
    for item in items:
        if not isinstance(item, dict):
            kept_items.append(item)
            continue
        item_payload = item.get("payload")
        if isinstance(item_payload, dict):
            # exact/balanced：媒体地址在 payload 里
            rewrite_minio_media_fields(item_payload)
            # 与以图搜人一致：无图片地址的条目前端只能渲染成裂图卡片，丢弃
            if str(item_payload.get("image_url") or "").strip():
                kept_items.append(item)
            continue
        # fuzzy：精简字段在条目顶层（es_id/image_url/...）
        rewrite_minio_media_fields(item)
        if str(item.get("image_url") or "").strip():
            kept_items.append(item)
    data["items"] = kept_items
    return response
