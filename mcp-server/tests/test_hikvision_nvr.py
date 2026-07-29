import asyncio
from datetime import datetime, timedelta, timezone

from app.hikvision_nvr import HikvisionNvrClient, _build_rtsp_fallback, build_rtsp_direct_recording, build_search_body, parse_search_response
from app.models import Camera


def test_build_search_body_contains_track_and_utc_range():
    body = build_search_body(
        "101",
        datetime(2026, 6, 22, 1, 2, 3, tzinfo=timezone.utc),
        datetime(2026, 6, 22, 2, 2, 3, tzinfo=timezone.utc),
        500,
    )

    assert '<CMSearchDescription version="1.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">' in body
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


def test_parse_search_response_adds_rtsp_credentials_for_internal_playback():
    camera = Camera(
        id="cam-1",
        name="Gate",
        sourceUrl="",
        streamApp="live",
        streamName="",
        status="STOPPED",
        playbackUrl="",
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        nvrTrackId="601",
    )
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <CMSearchResult xmlns="http://www.hikvision.com/ver20/XMLSchema">
      <matchList>
        <searchMatchItem>
          <trackID>601</trackID>
          <timeSpan>
            <startTime>2026-02-17T00:00:00Z</startTime>
            <endTime>2026-02-17T00:16:06Z</endTime>
          </timeSpan>
          <mediaSegmentDescriptor>
            <playbackURI>rtsp://192.168.11.251/Streaming/tracks/601/?starttime=20260217T000000Z</playbackURI>
          </mediaSegmentDescriptor>
        </searchMatchItem>
      </matchList>
    </CMSearchResult>"""

    recordings = parse_search_response(xml, camera, "601", 50, "admin", "p@ss&")

    assert recordings[0].playbackUri.startswith("rtsp://admin:p%40ss%26@192.168.11.251/")
    assert recordings[0].model_dump().get("playbackUri") is None


def test_rtsp_fallback_does_not_expose_nvr_credentials_in_metadata():
    start = datetime(2026, 6, 22, 1, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 6, 22, 1, 10, 0, tzinfo=timezone.utc)
    camera = Camera(
        id="cam-1",
        name="Gate",
        sourceUrl="",
        streamApp="live",
        streamName="",
        status="STOPPED",
        playbackUrl="",
        createdAt=start,
        updatedAt=start,
        nvrTrackId="101",
    )

    recordings = _build_rtsp_fallback(camera, "101", start, end, "192.168.11.251", "admin", "secret", 1)

    assert recordings
    assert recordings[0].metadata.get("nvrUsername") is None
    assert recordings[0].metadata.get("nvrPassword") is None
    assert recordings[0].model_dump().get("playbackUri") is None


def test_build_rtsp_direct_recording_uses_prompt_time_range_and_credentials():
    tz = timezone(timedelta(hours=8))
    start = datetime(2025, 8, 26, 16, 0, 0, tzinfo=tz)
    end = datetime(2025, 8, 26, 17, 0, 0, tzinfo=tz)
    camera = Camera(
        id="192.168.11.251-track-601",
        name="NVR-192.168.11.251-601",
        sourceUrl="",
        streamApp="live",
        streamName="",
        status="STOPPED",
        playbackUrl="",
        createdAt=start,
        updatedAt=start,
        nvrId="192.168.11.251",
        nvrChannel="601",
        nvrTrackId="601",
        nvrStreamType="main",
    )

    recording = build_rtsp_direct_recording(camera, "601", start, end, "192.168.11.251", "admin", "cisdi@123&")

    assert recording.playbackUri == (
        "rtsp://admin:cisdi%40123%26@192.168.11.251:554"
        "/Streaming/tracks/601?starttime=20250826T160000Z&endtime=20250826T170000Z"
    )
    assert recording.source == "hikvision_rtsp_direct"
    assert recording.model_dump().get("playbackUri") is None


def test_search_by_track_builds_direct_rtsp_without_nvr_search():
    client = HikvisionNvrClient("http://192.168.11.251", "admin", "cisdi@123&")
    tz = timezone(timedelta(hours=8))
    start = datetime(2025, 8, 26, 16, 0, 0, tzinfo=tz)
    end = datetime(2025, 8, 26, 17, 0, 0, tzinfo=tz)

    recordings = asyncio.run(client.search_by_track("601", start, end, 1))

    assert not hasattr(client, "_do_search")
    assert len(recordings) == 1
    assert recordings[0].playbackUri == (
        "rtsp://admin:cisdi%40123%26@192.168.11.251:554"
        "/Streaming/tracks/601?starttime=20250826T160000Z&endtime=20250826T170000Z"
    )
