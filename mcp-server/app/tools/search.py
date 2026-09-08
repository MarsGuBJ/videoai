"""Text-to-image search and one-shot image-to-image person search MCP tools."""

import asyncio
from typing import Any

from ..context import mcp, person_api, retrieve_api

POLL_INTERVAL_SECONDS = 2.0
DEFAULT_WAIT_TIMEOUT_SECONDS = 120.0


@mcp.tool()
async def text_search_images(
    message: str = "",
    startTime: str = "",
    endTime: str = "",
    location: str = "",
    page: int = 1,
    pageSize: int = 10,
) -> dict:
    """Search person/vehicle images by natural language description (text-to-image retrieval).
    message is the Chinese description, e.g. "穿红衣服的人"; startTime/endTime and location
    optionally narrow the search. Returns the retrieval service response with matched items."""
    return await retrieve_api.text_search(message, startTime, endTime, location, page, pageSize)


@mcp.tool()
async def search_person_by_image(
    imageUrl: str = "",
    bbox: list[dict[str, Any]] | None = None,
    searchMethod: str = "reid",
    startTime: str = "",
    endTime: str = "",
    similarityThreshold: float = 0.6,
    topK: int = 10,
    waitTimeoutSeconds: float = DEFAULT_WAIT_TIMEOUT_SECONDS,
) -> dict:
    """One-shot image-to-image person search: detect the target person (when bbox is not
    given), submit the search task and poll until it finishes. Returns the final result
    including similar_persons. Raises ValueError when no person is detected, the task
    fails or times out."""
    if bbox is None:
        detect = await person_api.detect_persons(imageUrl)
        detect_data = detect.get("data") if isinstance(detect, dict) else None
        detected = (detect_data or {}).get("detected_persons") or []
        if not isinstance(detect_data, dict) or detect_data.get("status") != "success" or not detected:
            message = (detect_data or {}).get("message") or "未检测到人，请重新上传"
            raise ValueError(message)
        bbox = detected[0].get("bbox")
    submit = await person_api.search_person_by_bbox(
        imageUrl,
        bbox=bbox,
        search_method=searchMethod,
        start_time=startTime,
        end_time=endTime,
        similarity_threshold=similarityThreshold,
        top_k=topK,
    )
    submit_data = submit.get("data") if isinstance(submit, dict) else None
    # 上游存在 data.task_id 与 data.data.task_id 两种嵌套（同前端 ImageSearchPage 的兼容逻辑）
    task_id = (submit_data or {}).get("task_id") or ((submit_data or {}).get("data") or {}).get("task_id")
    if not task_id:
        message = (submit_data or {}).get("message") or "搜索任务提交失败"
        raise ValueError(message)
    return await poll_person_search_result(str(task_id), waitTimeoutSeconds)


async def poll_person_search_result(task_id: str, wait_timeout_seconds: float) -> dict:
    """Poll a person search task until it succeeds, fails or the wait budget runs out."""
    deadline = asyncio.get_running_loop().time() + max(wait_timeout_seconds, POLL_INTERVAL_SECONDS)
    while True:
        result = await person_api.get_person_search_result(task_id)
        data = result.get("data") if isinstance(result, dict) else None
        status = (data or {}).get("status")
        if status == "success":
            return result
        if status == "error":
            message = (data or {}).get("message") or "搜索任务失败"
            raise ValueError(message)
        if asyncio.get_running_loop().time() >= deadline:
            raise ValueError("搜索任务超时，请稍后重试")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
