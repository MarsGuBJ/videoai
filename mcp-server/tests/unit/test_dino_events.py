from datetime import datetime, timezone

from app.server import DINO_EVENT_COUNT, DINO_EVENT_TYPE, build_mock_dino_events, normalize_dino_event_limit
from app.xml_builder import build_dino_event_list_xml


def test_build_mock_dino_events_returns_ten_items_with_requested_fields():
    events = build_mock_dino_events(
        camera_names=["北门摄像头"],
        descriptions=["进入禁区"],
        base_time=datetime(2026, 7, 7, 8, 0, 0, tzinfo=timezone.utc),
    )

    assert len(events) == DINO_EVENT_COUNT
    assert events[0]["eventSource"] == "视觉平台"
    assert events[0]["eventType"] == DINO_EVENT_TYPE
    assert events[0]["eventStatus"] == "有效"
    assert events[0]["eventLevel"] == 1
    assert events[0]["eventLocation"] == "北门摄像头"
    assert events[0]["occurredAt"] == events[0]["reportedAt"]
    assert events[0]["eventImage"].startswith("data:image/svg+xml")
    assert events[0]["eventDescription"] == "进入禁区"


def test_build_mock_dino_events_defaults_missing_description_to_none_text():
    events = build_mock_dino_events(camera_names=["北门摄像头"], descriptions=[], count=1)

    assert events[0]["eventDescription"] == "无"


def test_normalize_dino_event_limit_caps_at_ten():
    assert normalize_dino_event_limit(500) == 10


def test_dino_event_xml_uses_expected_root_and_count():
    xml = build_dino_event_list_xml(build_mock_dino_events(camera_names=["北门摄像头"], count=2))

    assert '<sxin-dino-event-list count="2">' in xml
    assert 'eventType="DINO Object Detection"' in xml
