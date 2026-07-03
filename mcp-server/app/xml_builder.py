"""XML response builder for VideoAI MCP server — attribute-based format."""

from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring


def _attr(value, default: str = "") -> str:
    """Convert a value to a string suitable for an XML attribute."""
    if value is None:
        return default
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def build_camera_list_xml(cameras: list[dict]) -> str:
    """Build <sxin-camera-list> XML with attributes."""
    root = Element("sxin-camera-list")
    root.set("count", str(len(cameras)))
    for cam in cameras:
        c = SubElement(root, "camera")
        c.set("id", _attr(cam.get("cameraId")))
        c.set("name", _attr(cam.get("name")))
        c.set("status", _attr(cam.get("status")))
        c.set("livePlaybackUrl", _attr(cam.get("livePlaybackUrl")))
        c.set("sourceUrl", _attr(cam.get("sourceUrl")))
        binding = cam.get("nvrBinding", {})
        c.set("nvrBinding", _attr(binding.get("bound", False)))
        c.text = "\n  "
    return _xml_declaration() + _pretty(root)


def build_camera_flow_xml(data: dict) -> str:
    """Build <sxin-camera-flow> XML with attributes."""
    root = Element("sxin-camera-flow")
    root.set("url", _attr(data.get("url")))
    root.set("format", _attr(data.get("format")))
    root.set("source", _attr(data.get("source")))
    expires = data.get("expiresAt")
    if isinstance(expires, datetime):
        expires = expires.isoformat()
    root.set("expiresAt", _attr(expires, ""))
    meta = data.get("metadata", {})
    root.set("cameraId", _attr(meta.get("cameraId")))
    root.set("cameraName", _attr(meta.get("cameraName")))
    root.set("status", _attr(meta.get("status")))
    return _xml_declaration() + _pretty(root)


def build_video_list_xml(recordings: list[dict]) -> str:
    """Build <sxin-video-list> XML with attributes."""
    root = Element("sxin-video-list")
    root.set("count", str(len(recordings)))
    for rec in recordings:
        r = SubElement(root, "recording")
        r.set("recordingId", _attr(rec.get("recordingId")))
        r.set("cameraId", _attr(rec.get("cameraId")))
        r.set("cameraName", _attr(rec.get("cameraName")))
        r.set("trackId", _attr(rec.get("trackId")))
        start = rec.get("startTime")
        if isinstance(start, datetime):
            start = start.isoformat()
        r.set("startTime", _attr(start))
        end = rec.get("endTime")
        if isinstance(end, datetime):
            end = end.isoformat()
        r.set("endTime", _attr(end))
        r.set("source", _attr(rec.get("source")))
        r.set("streamUrl", _attr(rec.get("streamUrl")))
        meta = rec.get("metadata", {})
        r.set("nvrId", _attr(meta.get("nvrId")))
        r.text = "\n  "
    return _xml_declaration() + _pretty(root)


def build_video_file_xml(data: dict) -> str:
    """Build <sxin-video-file> XML with attributes."""
    root = Element("sxin-video-file")
    root.set("url", _attr(data.get("url")))
    root.set("format", _attr(data.get("format")))
    root.set("source", _attr(data.get("source")))
    expires = data.get("expiresAt")
    if isinstance(expires, datetime):
        expires = expires.isoformat()
    root.set("expiresAt", _attr(expires, ""))
    meta = data.get("metadata", {})
    root.set("cameraId", _attr(meta.get("cameraId")))
    root.set("cameraName", _attr(meta.get("cameraName")))
    root.set("recordingId", _attr(meta.get("recordingId")))
    root.set("trackId", _attr(meta.get("trackId")))
    start = meta.get("startTime")
    if isinstance(start, datetime):
        start = start.isoformat()
    root.set("startTime", _attr(start))
    end = meta.get("endTime")
    if isinstance(end, datetime):
        end = end.isoformat()
    root.set("endTime", _attr(end))
    return _xml_declaration() + _pretty(root)


def _pretty(element: Element) -> str:
    """Return pretty-printed XML string with indentation (no declaration)."""
    import xml.dom.minidom
    raw = tostring(element, encoding="unicode")
    dom = xml.dom.minidom.parseString(raw)
    # Remove extra XML declaration from minidom
    result = dom.toprettyxml(indent=" ")
    if result.startswith("<?xml"):
        result = result[result.index("?>") + 2:].lstrip("\n")
    return result


def _xml_declaration() -> str:
    return '<?xml version="1.0" encoding="UTF-8"?>\n'
