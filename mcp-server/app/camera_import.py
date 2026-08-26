from __future__ import annotations

import argparse
import csv
import json
import logging
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from ipaddress import ip_address
from itertools import permutations
from pathlib import Path
from typing import Literal
from urllib.parse import quote, urlparse
from urllib.request import (
    HTTPDigestAuthHandler,
    HTTPPasswordMgrWithDefaultRealm,
    Request,
    build_opener,
    urlopen,
)
from xml.etree import ElementTree

from .hcnetsdk_playback import HcNetSdkLibrary
from .settings import load_settings

logger = logging.getLogger(__name__)

EXPECTED_ROW_COUNT = 359
EXPECTED_HOST_COUNT = 336
EXPECTED_DUPLICATE_HOST_GROUPS = 23


@dataclass(frozen=True)
class CameraRow:
    sequence: str
    name: str
    area: str
    camera_type: str
    device_name: str
    host: str
    sdk_port: int

    @property
    def import_key(self) -> tuple[str, str, str]:
        return self.sequence, self.name, self.host


@dataclass(frozen=True)
class StreamChannel:
    streaming_id: int
    name: str
    rtsp_port: int = 554


@dataclass(frozen=True)
class ChannelMapping:
    row: CameraRow
    channel: StreamChannel


@dataclass(frozen=True)
class ImportOperation:
    action: Literal["create", "update", "skip"]
    row: CameraRow
    channel: StreamChannel
    payload: dict[str, str]
    camera_id: str | None = None


def parse_isapi_channels(xml: bytes, rtsp_port: int = 554) -> list[StreamChannel]:
    """Parse the ISAPI StreamingChannel list and return main-stream channels.

    Args:
        xml: Raw ISAPI ``/ISAPI/Streaming/channels`` response body.
        rtsp_port: RTSP port to record on each returned channel.

    Returns:
        Main-stream channels sorted by streaming id.
    """
    root = ElementTree.fromstring(xml)  # noqa: S314  # XML 来自内网受信 NVR 的 ISAPI 响应
    channels: list[StreamChannel] = []
    for element in root.iter():
        if _local_name(element.tag) != "StreamingChannel":
            continue
        values = {_local_name(child.tag): (child.text or "").strip() for child in element}
        raw_id = values.get("id", "")
        if not raw_id.isdigit():
            continue
        streaming_id = int(raw_id)
        if streaming_id % 100 != 1:
            continue
        channels.append(
            StreamChannel(
                streaming_id=streaming_id,
                name=values.get("channelName") or f"Channel {streaming_id // 100}",
                rtsp_port=rtsp_port,
            )
        )
    return sorted(channels, key=lambda channel: channel.streaming_id)


def parse_rtsp_port(xml: bytes) -> int:
    """Extract the RTSP port from an ISAPI network ports response, defaulting to 554."""
    root = ElementTree.fromstring(xml)  # noqa: S314  # XML 来自内网受信 NVR 的 ISAPI 响应
    for element in root.iter():
        local_name = _local_name(element.tag)
        if local_name == "rtspPortNo" and (element.text or "").strip().isdigit():
            return int((element.text or "").strip())
        if local_name != "RTSP":
            continue
        for child in element.iter():
            value = (child.text or "").strip()
            if _local_name(child.tag) == "portNo" and value.isdigit():
                return int(value)
    return 554


def discover_device_channels(
    row: CameraRow,
    username: str,
    password: str,
    *,
    isapi_request=None,
    sdk_library=None,
) -> list[StreamChannel]:
    """Discover main-stream channels for one device, preferring ISAPI and falling back to HCNetSDK.

    Args:
        row: Manifest row describing the device.
        username: Device login username.
        password: Device login password.
        isapi_request: Optional override for the ISAPI GET callable (testing).
        sdk_library: Optional override for the HCNetSDK library (testing).

    Returns:
        Discovered main-stream channels.
    """
    if isapi_request is None:

        def isapi_request(path):
            return _digest_get(f"http://{row.host}{path}", username, password)

    rtsp_port = 554
    try:
        try:
            rtsp_port = parse_rtsp_port(isapi_request("/ISAPI/System/Network/ports"))
        except Exception:  # noqa: BLE001  # 端口探测失败时回退默认 554
            rtsp_port = 554
        channels = parse_isapi_channels(isapi_request("/ISAPI/Streaming/channels"), rtsp_port)
        if channels:
            return channels
    except Exception:  # noqa: S110, BLE001  # ISAPI 不可用时静默回退 HCNetSDK 通道发现
        pass

    if sdk_library is None:
        sdk_library = HcNetSdkLibrary.instance()
    session = sdk_library.login_with_device_info(row.host, row.sdk_port, username, password)
    try:
        channels = [StreamChannel(channel * 100 + 1, f"Channel {channel}") for channel in session.channels]
        if not channels:
            raise ValueError(f"{row.host}: HCNetSDK reported no channels")
        return channels
    finally:
        sdk_library.sdk.NET_DVR_Logout(session.user_id)


def discover_and_map(
    rows: list[CameraRow],
    username: str,
    password: str,
    *,
    discoverer=discover_device_channels,
    max_workers: int = 16,
) -> tuple[list[ChannelMapping], list[dict]]:
    """Discover channels for all manifest rows concurrently and map rows to channels.

    Args:
        rows: Manifest rows to map.
        username: Device login username.
        password: Device login password.
        discoverer: Channel discovery callable (testing override).
        max_workers: Thread pool size for per-host discovery.

    Returns:
        A ``(mappings, failures)`` pair; failures carry host, row sequences and
        a password-redacted error message.
    """
    rows_by_host: dict[str, list[CameraRow]] = defaultdict(list)
    for row in rows:
        rows_by_host[row.host].append(row)
    row_order = {row.import_key: index for index, row in enumerate(rows)}
    host_order = {host: index for index, host in enumerate(rows_by_host)}
    mappings: list[ChannelMapping] = []
    failures: list[dict] = []

    def discover_host(host_rows: list[CameraRow]) -> list[ChannelMapping]:
        channels = discoverer(host_rows[0], username, password)
        return map_camera_rows(host_rows, channels)

    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as executor:
        futures = {
            executor.submit(discover_host, host_rows): (host, host_rows) for host, host_rows in rows_by_host.items()
        }
        for future in as_completed(futures):
            host, host_rows = futures[future]
            try:
                mappings.extend(future.result())
            except Exception as exc:  # noqa: BLE001  # 单台主机失败记入 failures，不中断其余主机
                failures.append(
                    {
                        "host": host,
                        "sequences": [row.sequence for row in host_rows],
                        "failedRows": len(host_rows),
                        "error": _safe_error(exc, password),
                    }
                )
    mappings.sort(key=lambda mapping: row_order[mapping.row.import_key])
    failures.sort(key=lambda failure: host_order[failure["host"]])
    return mappings, failures


def _safe_error(error: Exception, password: str) -> str:
    message = str(error) or type(error).__name__
    return message.replace(password, "***") if password else message


def _digest_get(url: str, username: str, password: str, timeout: float = 5.0) -> bytes:
    password_manager = HTTPPasswordMgrWithDefaultRealm()
    password_manager.add_password(None, url, username, password)
    opener = build_opener(HTTPDigestAuthHandler(password_manager))
    # URL 来自清单中的内网设备地址
    request = Request(url, headers={"Accept": "application/xml", "User-Agent": "VideoAI-Camera-Import/1.0"})  # noqa: S310
    with opener.open(request, timeout=timeout) as response:
        return response.read()


def map_camera_rows(rows: list[CameraRow], channels: list[StreamChannel]) -> list[ChannelMapping]:
    """Map manifest rows to discovered channels using name/kind scoring.

    Raises:
        ValueError: If no channels were discovered or the mapping is ambiguous.
    """
    if not rows:
        return []
    if not channels:
        raise ValueError(f"{rows[0].host}: no main-stream channels were discovered")
    if len(channels) < len(rows):
        raise ValueError(f"{rows[0].host}: channel mapping is ambiguous")
    if len(rows) == 1:
        normalized_name = _normalize_name(rows[0].name)
        channel = next(
            (item for item in channels if _normalize_name(item.name) == normalized_name),
            channels[0],
        )
        return [ChannelMapping(row=rows[0], channel=channel)]

    ordered_channels = sorted(channels, key=lambda channel: channel.streaming_id)
    candidates: list[tuple[int, tuple[StreamChannel, ...]]] = []
    for selected_channels in permutations(ordered_channels, len(rows)):
        score = sum(_mapping_score(row, channel) for row, channel in zip(rows, selected_channels, strict=True))
        candidates.append((score, selected_channels))
    best_score = max(score for score, _ in candidates)
    best = [selected for score, selected in candidates if score == best_score]
    if best_score > 0 and len(best) == 1:
        selected = best[0]
    elif len(rows) == len(ordered_channels):
        selected = tuple(ordered_channels)
    else:
        raise ValueError(f"{rows[0].host}: channel mapping is ambiguous")
    return [ChannelMapping(row=row, channel=channel) for row, channel in zip(rows, selected, strict=True)]


def build_camera_payload(mapping: ChannelMapping, username: str, password: str) -> dict[str, str]:
    """Build the backend camera create/update payload for one mapping."""
    row = mapping.row
    channel = mapping.channel
    credentials = f"{quote(username, safe='')}:{quote(password, safe='')}@"
    source_url = f"rtsp://{credentials}{row.host}:{channel.rtsp_port}/Streaming/Channels/{channel.streaming_id}"
    return {
        "name": row.name,
        "sourceUrl": source_url,
        "description": _import_marker(row),
        "area": row.area,
        "nvrId": row.host,
        "nvrChannel": str(channel.streaming_id // 100),
        "nvrTrackId": str(channel.streaming_id),
        "nvrStreamType": "main",
    }


def plan_import(
    mappings: list[ChannelMapping],
    existing_cameras: list[dict],
    username: str,
    password: str,
) -> list[ImportOperation]:
    """Diff mappings against existing cameras and plan create/update/skip operations."""
    used_camera_ids: set[str] = set()
    operations: list[ImportOperation] = []
    for mapping in mappings:
        payload = build_camera_payload(mapping, username, password)
        marker = _import_marker(mapping.row)
        existing = next(
            (
                camera
                for camera in existing_cameras
                if str(camera.get("id", "")) not in used_camera_ids and str(camera.get("description") or "") == marker
            ),
            None,
        )
        if existing is None:
            existing = next(
                (
                    camera
                    for camera in existing_cameras
                    if str(camera.get("id", "")) not in used_camera_ids
                    and camera.get("name") == mapping.row.name
                    and _existing_camera_host(camera) == mapping.row.host
                ),
                None,
            )
        if existing is None:
            operations.append(ImportOperation("create", mapping.row, mapping.channel, payload))
            continue
        camera_id = str(existing["id"])
        used_camera_ids.add(camera_id)
        action: Literal["update", "skip"] = (
            "skip" if all(existing.get(key) == value for key, value in payload.items()) else "update"
        )
        operations.append(ImportOperation(action, mapping.row, mapping.channel, payload, camera_id))
    return operations


def apply_import_operations(
    operations: list[ImportOperation],
    backend_url: str,
    *,
    apply_changes: bool,
    request_json=None,
) -> dict[str, int | bool]:
    """Execute planned operations against the backend and return a write summary.

    With ``apply_changes=False`` only counts what would change (dry-run).
    """
    summary: dict[str, int | bool] = {
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "failed": 0,
        "applied": apply_changes,
    }
    if not apply_changes:
        for operation in operations:
            key = {"create": "created", "update": "updated", "skip": "skipped"}[operation.action]
            summary[key] = int(summary[key]) + 1
        return summary

    requester = request_json or _request_json
    base_url = backend_url.rstrip("/")
    for operation in operations:
        if operation.action == "skip":
            summary["skipped"] = int(summary["skipped"]) + 1
            continue
        method = "POST" if operation.action == "create" else "PATCH"
        url = f"{base_url}/api/cameras"
        if operation.action == "update":
            url = f"{url}/{operation.camera_id}"
        try:
            requester(method, url, operation.payload)
        except Exception:  # noqa: BLE001  # 单条写入失败计入 failed，继续后续操作
            summary["failed"] = int(summary["failed"]) + 1
        else:
            key = "created" if operation.action == "create" else "updated"
            summary[key] = int(summary[key]) + 1
    return summary


def run_import(
    rows: list[CameraRow],
    username: str,
    password: str,
    backend_url: str,
    *,
    apply_changes: bool,
    discoverer=discover_device_channels,
    request_json=None,
    max_workers: int = 16,
) -> dict:
    """Run the full import pipeline: fetch existing cameras, discover, plan and apply.

    Returns:
        Summary dict with input/mapping counts, write summary and discovery failures.
    """
    requester = request_json or _request_json
    existing_cameras = requester("GET", f"{backend_url.rstrip('/')}/api/cameras")
    mappings, discovery_failures = discover_and_map(
        rows,
        username,
        password,
        discoverer=discoverer,
        max_workers=max_workers,
    )
    operations = plan_import(mappings, existing_cameras, username, password)
    write_summary = apply_import_operations(
        operations,
        backend_url,
        apply_changes=apply_changes,
        request_json=requester,
    )
    discovery_failed_rows = sum(int(failure["failedRows"]) for failure in discovery_failures)
    write_summary["failed"] = int(write_summary["failed"]) + discovery_failed_rows
    return {
        "inputRows": len(rows),
        "hosts": len({row.host for row in rows}),
        "mapped": len(mappings),
        **write_summary,
        "failures": discovery_failures,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint: parse args, load settings and run the import.

    Returns:
        Exit code: 0 on success, 1 when any row failed, 2 when credentials are missing.
    """
    parser = argparse.ArgumentParser(description="Discover and import Hikvision cameras into VideoAI")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Discover and plan changes without writing")
    mode.add_argument("--apply", action="store_true", help="Apply planned camera creates and updates")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).with_name("data") / "2026-07-29-cameras.csv",
    )
    parser.add_argument("--max-workers", type=int, default=16)
    args = parser.parse_args(argv)

    settings = load_settings()
    if not settings.camera_import_username or not settings.camera_import_password:
        logger.error("camera import credentials are not configured")
        return 2

    rows = load_camera_rows(args.manifest)
    summary = run_import(
        rows,
        settings.camera_import_username,
        settings.camera_import_password,
        settings.camera_import_backend_url,
        apply_changes=args.apply,
        max_workers=args.max_workers,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if int(summary["failed"]) else 0


def _request_json(method: str, url: str, payload: dict | None = None):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    # URL 来自配置的后端内网地址
    request = Request(  # noqa: S310
        url,
        data=body,
        method=method,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310
        content = response.read()
    return json.loads(content) if content else None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _normalize_name(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


def _import_marker(row: CameraRow) -> str:
    return f"camera-import:2026-07-29:{row.sequence}"


def _existing_camera_host(camera: dict) -> str:
    nvr_id = str(camera.get("nvrId") or "").strip()
    if nvr_id:
        return nvr_id
    return urlparse(str(camera.get("sourceUrl") or "")).hostname or ""


def _mapping_score(row: CameraRow, channel: StreamChannel) -> int:
    row_name = _normalize_name(row.name)
    channel_name = _normalize_name(channel.name)
    score = 0
    if row_name and row_name == channel_name:
        score += 1000
    elif min(len(row_name), len(channel_name)) >= 4 and (row_name in channel_name or channel_name in row_name):
        score += 200
    row_kind = _stream_kind(f"{row.name} {row.camera_type} {row.device_name}")
    channel_kind = _stream_kind(channel.name)
    if row_kind and row_kind == channel_kind:
        score += 100
    return score


def _stream_kind(value: str) -> str:
    normalized = _normalize_name(value)
    if any(keyword in normalized for keyword in ("普通", "可见", "光学", "visible", "optical")):
        return "visible"
    if any(keyword in normalized for keyword in ("热成像", "热像", "thermal")):
        return "thermal"
    if "云台枪机" in normalized or "ptz" in normalized:
        return "ptz"
    if "球机" in normalized or "dome" in normalized:
        return "dome"
    return ""


def load_camera_rows(path: Path) -> list[CameraRow]:
    """Load and validate the camera manifest CSV.

    Raises:
        ValueError: On missing values, invalid hosts/ports, duplicate keys or
            unexpected row/host/group counts.
    """
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        records = list(csv.DictReader(handle))

    rows: list[CameraRow] = []
    for line_number, record in enumerate(records, start=2):
        required = {key: (record.get(key) or "").strip() for key in ("sequence", "name", "area", "host")}
        if not all(required.values()):
            raise ValueError(f"manifest line {line_number} is missing a required value")
        host = required["host"]
        if ip_address(host).version != 4:
            raise ValueError(f"manifest line {line_number} does not contain an IPv4 address")
        sdk_port = int((record.get("sdk_port") or "0").strip())
        if not 1 <= sdk_port <= 65535:
            raise ValueError(f"manifest line {line_number} contains an invalid SDK port")
        rows.append(
            CameraRow(
                sequence=required["sequence"],
                name=required["name"],
                area=required["area"],
                camera_type=(record.get("camera_type") or "").strip(),
                device_name=(record.get("device_name") or "").strip(),
                host=host,
                sdk_port=sdk_port,
            )
        )

    keys = [row.import_key for row in rows]
    if len(set(keys)) != len(keys):
        raise ValueError("manifest contains duplicate import keys")
    host_counts = Counter(row.host for row in rows)
    duplicate_host_groups = sum(count > 1 for count in host_counts.values())
    if len(rows) != EXPECTED_ROW_COUNT:
        raise ValueError(f"manifest must contain {EXPECTED_ROW_COUNT} rows")
    if len(host_counts) != EXPECTED_HOST_COUNT:
        raise ValueError(f"manifest must contain {EXPECTED_HOST_COUNT} unique hosts")
    if duplicate_host_groups != EXPECTED_DUPLICATE_HOST_GROUPS:
        raise ValueError(f"manifest must contain {EXPECTED_DUPLICATE_HOST_GROUPS} duplicate-host groups")
    return rows


if __name__ == "__main__":
    raise SystemExit(main())
