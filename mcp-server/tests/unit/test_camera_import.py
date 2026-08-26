import runpy
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from app.camera_import import (
    CameraRow,
    ChannelMapping,
    StreamChannel,
    apply_import_operations,
    build_camera_payload,
    discover_and_map,
    discover_device_channels,
    load_camera_rows,
    map_camera_rows,
    parse_isapi_channels,
    plan_import,
    run_import,
)


def test_module_entrypoint_defines_loader_before_main(tmp_path, monkeypatch):
    manifest = tmp_path / "empty.csv"
    manifest.write_text(
        "sequence,name,area,camera_type,device_name,host,sdk_port\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CAMERA_IMPORT_USERNAME", "admin")
    monkeypatch.setenv("CAMERA_IMPORT_PASSWORD", "secret")
    monkeypatch.setattr(
        sys,
        "argv",
        ["camera_import", "--dry-run", "--manifest", str(manifest)],
    )

    with pytest.raises(ValueError, match="359"):
        runpy.run_module("app.camera_import", run_name="__main__")


MANIFEST = Path(__file__).parents[2] / "app" / "data" / "2026-07-29-cameras.csv"


def make_row(sequence: str, name: str, camera_type: str = "枪机") -> CameraRow:
    return CameraRow(
        sequence=sequence,
        name=name,
        area="赛迪电气/厂房",
        camera_type=camera_type,
        device_name=name,
        host="10.10.0.1",
        sdk_port=8000,
    )


def test_manifest_contains_all_spreadsheet_rows():
    rows = load_camera_rows(MANIFEST)

    assert len(rows) == 359
    assert len({row.host for row in rows}) == 336


def test_parse_isapi_channels_returns_only_main_streams():
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <StreamingChannelList xmlns="http://www.hikvision.com/ver20/XMLSchema">
      <StreamingChannel><id>101</id><channelName>Visible Camera</channelName></StreamingChannel>
      <StreamingChannel><id>102</id><channelName>Visible Camera Sub</channelName></StreamingChannel>
      <StreamingChannel><id>201</id><channelName>Thermal Camera</channelName></StreamingChannel>
      <StreamingChannel><id>202</id><channelName>Thermal Camera Sub</channelName></StreamingChannel>
    </StreamingChannelList>
    """

    channels = parse_isapi_channels(xml)

    assert [(channel.streaming_id, channel.name) for channel in channels] == [
        (101, "Visible Camera"),
        (201, "Thermal Camera"),
    ]


def test_map_camera_rows_maps_one_row_to_one_channel():
    mappings = map_camera_rows(
        [make_row("1", "南面围墙枪机01")],
        [StreamChannel(101, "南面围墙枪机01")],
    )

    assert mappings[0].row.sequence == "1"
    assert mappings[0].channel.streaming_id == 101


def test_map_camera_rows_distinguishes_visible_and_thermal_channels():
    mappings = map_camera_rows(
        [
            make_row("1", "配电室热成像枪机普通画面"),
            make_row("2", "配电室热成像画面"),
        ],
        [
            StreamChannel(201, "Thermal Camera"),
            StreamChannel(101, "Visible Camera"),
        ],
    )

    assert [mapping.channel.streaming_id for mapping in mappings] == [101, 201]


def test_map_camera_rows_matches_ball_and_ptz_names():
    mappings = map_camera_rows(
        [
            make_row("1", "厂房东南角立杆球机", "球机"),
            make_row("2", "厂房东南角立杆云台枪机", "云台枪机"),
        ],
        [
            StreamChannel(201, "厂房东南角立杆云台枪机"),
            StreamChannel(101, "厂房东南角立杆球机"),
        ],
    )

    assert [mapping.channel.streaming_id for mapping in mappings] == [101, 201]


def test_map_camera_rows_keeps_duplicate_names_distinct_by_sequence():
    mappings = map_camera_rows(
        [make_row("58", "低压配电室热成像枪机05"), make_row("59", "低压配电室热成像枪机05")],
        [StreamChannel(201, "Channel 2"), StreamChannel(101, "Channel 1")],
    )

    assert [(mapping.row.sequence, mapping.channel.streaming_id) for mapping in mappings] == [
        ("58", 101),
        ("59", 201),
    ]


def test_map_camera_rows_rejects_reusing_one_channel_for_two_rows():
    with pytest.raises(ValueError, match="ambiguous"):
        map_camera_rows(
            [make_row("1", "球机", "球机"), make_row("2", "云台枪机", "云台枪机")],
            [StreamChannel(101, "Camera")],
        )


def test_plan_import_skips_identical_mapping():
    mapping = ChannelMapping(make_row("341", "C轴枪机13"), StreamChannel(101, "C轴枪机13"))
    payload = build_camera_payload(mapping, "admin", "secret")
    existing = [{"id": "camera-1", **payload}]

    operations = plan_import([mapping], existing, "admin", "secret")

    assert [(operation.action, operation.camera_id) for operation in operations] == [("skip", "camera-1")]


def test_plan_import_updates_changed_channel():
    mapping = ChannelMapping(make_row("341", "C轴枪机13"), StreamChannel(201, "C轴枪机13"))
    existing_payload = build_camera_payload(
        ChannelMapping(mapping.row, StreamChannel(101, "C轴枪机13")),
        "admin",
        "secret",
    )
    existing = [{"id": "camera-1", **existing_payload}]

    operations = plan_import([mapping], existing, "admin", "secret")

    assert operations[0].action == "update"
    assert operations[0].camera_id == "camera-1"
    assert operations[0].payload["nvrTrackId"] == "201"


def test_plan_import_creates_missing_mapping():
    mapping = ChannelMapping(make_row("341", "C轴枪机13"), StreamChannel(101, "C轴枪机13"))

    operations = plan_import([mapping], [], "admin", "secret")

    assert operations[0].action == "create"
    assert operations[0].camera_id is None


def test_discover_device_channels_prefers_isapi_channels_and_rtsp_port():
    responses = {
        "/ISAPI/System/Network/ports": b"<NetworkPorts><RTSP><portNo>8554</portNo></RTSP></NetworkPorts>",
        "/ISAPI/Streaming/channels": (
            b"<StreamingChannelList><StreamingChannel><id>101</id>"
            b"<channelName>Main</channelName></StreamingChannel></StreamingChannelList>"
        ),
    }

    channels = discover_device_channels(
        make_row("1", "Camera"),
        "admin",
        "secret",
        isapi_request=lambda path: responses[path],
    )

    assert channels == [StreamChannel(101, "Main", 8554)]


def test_discover_device_channels_falls_back_to_hcnetsdk_and_logs_out():
    calls = []

    class FakeNativeSdk:
        @staticmethod
        def NET_DVR_Logout(user_id):
            calls.append(("logout", user_id))
            return True

    class FakeSdkLibrary:
        sdk = FakeNativeSdk()

        @staticmethod
        def login_with_device_info(host, port, username, password):
            calls.append(("login", host, port, username, password))
            return type("Session", (), {"user_id": 7, "channels": (1, 2)})()

    def failed_isapi(_path):
        raise OSError("ISAPI unavailable")

    channels = discover_device_channels(
        make_row("1", "Camera"),
        "admin",
        "secret",
        isapi_request=failed_isapi,
        sdk_library=FakeSdkLibrary(),
    )

    assert channels == [StreamChannel(101, "Channel 1"), StreamChannel(201, "Channel 2")]
    assert calls[-1] == ("logout", 7)


def test_apply_import_operations_dry_run_makes_no_requests():
    mappings = [ChannelMapping(make_row("1", "Camera 1"), StreamChannel(101, "Camera 1"))]
    operations = plan_import(mappings, [], "admin", "secret")
    calls = []

    summary = apply_import_operations(
        operations,
        "http://backend:8081",
        apply_changes=False,
        request_json=lambda *args: calls.append(args),
    )

    assert summary == {"created": 1, "updated": 0, "skipped": 0, "failed": 0, "applied": False}
    assert calls == []


def test_apply_import_operations_calls_only_create_and_update_endpoints():
    create_mapping = ChannelMapping(make_row("1", "Camera 1"), StreamChannel(101, "Camera 1"))
    update_mapping = ChannelMapping(make_row("2", "Camera 2"), StreamChannel(201, "Camera 2"))
    skip_mapping = ChannelMapping(make_row("3", "Camera 3"), StreamChannel(301, "Camera 3"))
    update_existing = {"id": "update-id", **build_camera_payload(update_mapping, "admin", "old-secret")}
    skip_existing = {"id": "skip-id", **build_camera_payload(skip_mapping, "admin", "secret")}
    operations = plan_import(
        [create_mapping, update_mapping, skip_mapping],
        [update_existing, skip_existing],
        "admin",
        "secret",
    )
    calls = []

    summary = apply_import_operations(
        operations,
        "http://backend:8081",
        apply_changes=True,
        request_json=lambda method, url, payload=None: calls.append((method, url, payload)) or {},
    )

    assert summary == {"created": 1, "updated": 1, "skipped": 1, "failed": 0, "applied": True}
    assert [(method, url) for method, url, _ in calls] == [
        ("POST", "http://backend:8081/api/cameras"),
        ("PATCH", "http://backend:8081/api/cameras/update-id"),
    ]


def test_discover_and_map_keeps_successes_when_one_device_fails():
    good = make_row("1", "Camera 1")
    failed = replace(make_row("2", "Camera 2"), host="10.10.0.2")

    def discover(row, _username, _password):
        if row.host == failed.host:
            raise OSError("device unreachable")
        return [StreamChannel(101, row.name)]

    mappings, failures = discover_and_map(
        [good, failed],
        "admin",
        "secret",
        discoverer=discover,
        max_workers=2,
    )

    assert [mapping.row.sequence for mapping in mappings] == ["1"]
    assert failures == [
        {
            "host": "10.10.0.2",
            "sequences": ["2"],
            "failedRows": 1,
            "error": "device unreachable",
        }
    ]


def test_run_import_counts_discovery_failures_in_total():
    good = make_row("1", "Camera 1")
    failed = replace(make_row("2", "Camera 2"), host="10.10.0.2")

    def discover(row, _username, _password):
        if row.host == failed.host:
            raise OSError("device unreachable")
        return [StreamChannel(101, row.name)]

    summary = run_import(
        [good, failed],
        "admin",
        "secret",
        "http://backend:8081",
        apply_changes=False,
        discoverer=discover,
        request_json=lambda method, url, payload=None: [] if method == "GET" else {},
        max_workers=2,
    )

    assert summary["inputRows"] == 2
    assert summary["hosts"] == 2
    assert summary["mapped"] == 1
    assert summary["created"] == 1
    assert summary["failed"] == 1
    assert summary["created"] + summary["updated"] + summary["skipped"] + summary["failed"] == 2
