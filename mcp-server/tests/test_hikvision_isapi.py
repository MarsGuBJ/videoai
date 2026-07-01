from datetime import datetime, timezone

from app.hikvision_isapi import build_search_body, parse_search_response
from app.models import Camera


def test_build_search_body_contains_track_and_utc_range():
    body = build_search_body(
        "101",
        datetime(2026, 6, 22, 1, 2, 3, tzinfo=timezone.utc),
        datetime(2026, 6, 22, 2, 2, 3, tzinfo=timezone.utc),
        500,
    )

    assert "<trackID>101</trackID>" in body
    assert "<startTime>2026-06-22T01:02:03Z</startTime>" in body
    assert "<maxResults>200</maxResults>" in body


def test_parse_search_response_hides_playback_uri_by_default():
    camera = Camera(
        id="cam-1",
        name="Gate",
        sourceUrl="rtsp://camera/live",
        streamApp="live",
        streamName="cam-1",
        status="RUNNING",
        playbackUrl="http://localhost/live/cam-1.m3u8",
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        nvrTrackId="101",
    )
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <CMSearchResult xmlns="http://www.hikvision.com/ver20/XMLSchema">
      <matchList>
        <searchMatchItem>
          <trackID>101</trackID>
          <timeSpan>
            <startTime>2026-06-22T01:00:00Z</startTime>
            <endTime>2026-06-22T01:10:00Z</endTime>
          </timeSpan>
          <mediaSegmentDescriptor>
            <playbackURI>rtsp://nvr/Streaming/tracks/101?starttime=...</playbackURI>
          </mediaSegmentDescriptor>
        </searchMatchItem>
      </matchList>
    </CMSearchResult>"""

    recordings = parse_search_response(xml, camera, "101", 50)

    assert len(recordings) == 1
    assert recordings[0].trackId == "101"
    assert recordings[0].model_dump().get("playbackUri") is None
