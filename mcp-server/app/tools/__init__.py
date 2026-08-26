"""MCP tool registrations, grouped by domain. Importing this package registers all tools."""

from .cameras import get_live_stream, list_cameras
from .dino import dino_events
from .faces import query_face_matches, upload_face_image
from .persons import (
    detect_persons,
    detect_persons_with_id,
    gait_feature_compare,
    get_person_bbox,
    get_person_search_result,
    search_person_by_bbox,
)
from .recordings import download_recording, get_recording_stream, search_recordings

__all__ = [
    "detect_persons",
    "detect_persons_with_id",
    "dino_events",
    "download_recording",
    "gait_feature_compare",
    "get_live_stream",
    "get_person_bbox",
    "get_person_search_result",
    "get_recording_stream",
    "list_cameras",
    "query_face_matches",
    "search_person_by_bbox",
    "search_recordings",
    "upload_face_image",
]
