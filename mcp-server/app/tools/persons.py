"""Person detection, search and gait comparison MCP tools."""

from typing import Any

from ..context import mcp, person_api


@mcp.tool()
async def detect_persons(imageUrl: str) -> dict:
    """Detect persons in an image URL and return person bounding boxes."""
    return await person_api.detect_persons(imageUrl)


@mcp.tool()
async def search_person_by_bbox(
    imageUrl: str,
    bbox: list[dict[str, Any]] | None = None,
    searchMethod: str = "reid",
    startTime: str = "",
    endTime: str = "",
    similarityThreshold: float = 0.6,
    topK: int = 10,
) -> dict:
    """Submit an async person image search task, optionally restricted to a bbox."""
    return await person_api.search_person_by_bbox(
        imageUrl,
        bbox=bbox,
        search_method=searchMethod,
        start_time=startTime,
        end_time=endTime,
        similarity_threshold=similarityThreshold,
        top_k=topK,
    )


@mcp.tool()
async def get_person_search_result(taskId: str) -> dict:
    """Poll a person image search task result by taskId."""
    return await person_api.get_person_search_result(taskId)


@mcp.tool()
async def detect_persons_with_id(imageUrl: str) -> dict:
    """Detect persons in an image URL and return cached person IDs with bounding boxes."""
    return await person_api.detect_persons_with_id(imageUrl)


@mcp.tool()
async def get_person_bbox(personId: str) -> dict:
    """Return cached bbox information for a personId from detect_persons_with_id."""
    return await person_api.get_person_bbox(personId)


@mcp.tool()
async def gait_feature_compare(persons: list[dict[str, Any]]) -> dict:
    """Compare gait features for a list of person records; the first person is the reference."""
    return await person_api.gait_feature_compare(persons)
