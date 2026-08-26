"""Mock DINO object-detection event MCP tool."""

import logging
from datetime import datetime, timedelta
from urllib.parse import quote

from ..context import (
    DEFAULT_RECORDING_TIMEZONE,
    DINO_DEFAULT_CAMERA_NAMES,
    DINO_EVENT_COUNT,
    DINO_EVENT_LEVEL,
    DINO_EVENT_SOURCE,
    DINO_EVENT_STATUS,
    DINO_EVENT_TYPE,
    mcp,
    videoai,
)
from ..xml_builder import build_dino_event_list_xml

logger = logging.getLogger(__name__)


@mcp.tool()
async def dino_events(limit: int = DINO_EVENT_COUNT) -> dict:
    """Return mock DINO Object Detection events for visual event search."""
    camera_names = await load_dino_event_camera_names()
    descriptions = await load_dino_event_descriptions()
    items = build_mock_dino_events(
        camera_names=camera_names,
        descriptions=descriptions,
        count=normalize_dino_event_limit(limit),
    )
    return {
        "data": items,
        "count": len(items),
        "xml": build_dino_event_list_xml(items),
    }


async def load_dino_event_camera_names() -> list[str]:
    try:
        cameras = await videoai.list_cameras()
    except Exception:  # 后端不可用时回退默认摄像头名单
        logger.exception("failed to load cameras for DINO events; falling back to default camera names")
        return list(DINO_DEFAULT_CAMERA_NAMES)
    names = [camera.name for camera in cameras if camera.name]
    return names or list(DINO_DEFAULT_CAMERA_NAMES)


async def load_dino_event_descriptions() -> list[str]:
    try:
        tasks = await videoai.list_deployment_tasks()
    except Exception:  # 后端不可用时回退空描述列表
        logger.exception("failed to load deployment tasks for DINO events; falling back to no descriptions")
        return []
    descriptions: list[str] = []
    for task in tasks:
        searchable = " ".join(str(task.get(key) or "") for key in ("name", "pipeline")).lower()
        if "dino" not in searchable:
            continue
        description = str(task.get("desc") or "").strip()
        if description:
            descriptions.append(description)
    return descriptions


def build_mock_dino_events(
    camera_names: list[str] | None = None,
    descriptions: list[str] | None = None,
    count: int = DINO_EVENT_COUNT,
    base_time: datetime | None = None,
) -> list[dict]:
    names = camera_names or list(DINO_DEFAULT_CAMERA_NAMES)
    notes = descriptions or []
    now = base_time or datetime.now(DEFAULT_RECORDING_TIMEZONE)
    if now.tzinfo is None:
        now = now.replace(tzinfo=DEFAULT_RECORDING_TIMEZONE)
    events = []
    for index in range(normalize_dino_event_limit(count)):
        occurred_at = now - timedelta(minutes=index * 5)
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=DEFAULT_RECORDING_TIMEZONE)
        description = notes[index % len(notes)] if notes else "无"
        events.append(
            {
                "eventId": f"dino-mock-{index + 1:03d}",
                "eventSource": DINO_EVENT_SOURCE,
                "eventType": DINO_EVENT_TYPE,
                "eventStatus": DINO_EVENT_STATUS,
                "eventLevel": DINO_EVENT_LEVEL,
                "eventLocation": names[index % len(names)],
                "occurredAt": occurred_at.isoformat(),
                "reportedAt": occurred_at.isoformat(),
                "eventImage": build_mock_dino_event_image(index + 1, names[index % len(names)]),
                "eventDescription": description,
            }
        )
    return events


def normalize_dino_event_limit(value: int) -> int:
    return max(1, min(int(value or DINO_EVENT_COUNT), DINO_EVENT_COUNT))


def build_mock_dino_event_image(index: int, camera_name: str) -> str:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">'
        '<rect width="640" height="360" fill="#111827"/>'
        '<rect x="28" y="28" width="584" height="304" fill="#1f2937" stroke="#60a5fa" stroke-width="4"/>'
        '<text x="48" y="78" fill="#e5e7eb" font-family="Arial, sans-serif" font-size="28">DINO Object Detection</text>'
        f'<text x="48" y="132" fill="#93c5fd" font-family="Arial, sans-serif" font-size="24">{camera_name}</text>'
        f'<text x="48" y="188" fill="#f9fafb" font-family="Arial, sans-serif" font-size="48">视频截图 {index:02d}'
        "</text>"
        '<rect x="410" y="168" width="128" height="86" fill="none" stroke="#22c55e" stroke-width="5"/>'
        '<text x="410" y="150" fill="#22c55e" font-family="Arial, sans-serif" font-size="22">object</text>'
        "</svg>"
    )
    return "data:image/svg+xml;charset=utf-8," + quote(svg, safe="")
