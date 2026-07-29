import json
from urllib.parse import parse_qs, urlsplit

import pytest

from preview_relay import PreviewRelayError, PreviewRelayManager, ZlmPreviewClient


SOURCE_URL = "rtsp://admin:password@10.10.0.93/Streaming/Channels/101"
SENSITIVE_VALUES = ("admin", "password", SOURCE_URL, "secret-value")


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        if isinstance(self.body, bytes):
            return self.body
        return json.dumps(self.body).encode("utf-8")


class FakeOpener:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.urls = []

    def __call__(self, request, timeout=None):
        self.urls.append(getattr(request, "full_url", request))
        return FakeResponse(self.responses.pop(0))


def make_zlm_client(opener):
    return ZlmPreviewClient(
        base_url="http://zlm:82",
        secret="secret-value",
        preview_rtmp_base="rtmp://127.0.0.1/live",
        command_key="ffmpeg.cmd_preview_h264",
        timeout_ms=15_000,
        opener=opener,
    )


def assert_sensitive_values_absent(error):
    message = str(error).casefold()
    for sensitive_value in SENSITIVE_VALUES:
        assert sensitive_value.casefold() not in message


def test_start_requests_preview_ffmpeg_source_and_returns_key():
    opener = FakeOpener({"code": 0, "data": {"key": "source-key-1"}})
    client = make_zlm_client(opener)

    key = client.start(stream_name="camera-1", source_url=SOURCE_URL)

    requested = urlsplit(opener.urls[0])
    query = parse_qs(requested.query)
    assert key == "source-key-1"
    assert requested.path == "/index/api/addFFmpegSource"
    assert query["secret"] == ["secret-value"]
    assert query["src_url"] == [SOURCE_URL]
    assert query["dst_url"] == ["rtmp://127.0.0.1/live/preview-camera-1"]
    assert query["timeout_ms"] == ["15000"]
    assert query["enable_hls"] == ["0"]
    assert query["enable_mp4"] == ["0"]
    assert query["ffmpeg_cmd_key"] == ["ffmpeg.cmd_preview_h264"]


def test_stop_deletes_ffmpeg_source_by_key():
    opener = FakeOpener({"code": 0})
    client = make_zlm_client(opener)

    client.stop("source-key-1")

    requested = urlsplit(opener.urls[0])
    assert requested.path == "/index/api/delFFmpegSource"
    assert parse_qs(requested.query) == {
        "secret": ["secret-value"],
        "key": ["source-key-1"],
    }


@pytest.mark.parametrize(
    "response",
    [
        {
            "code": -1,
            "msg": f"could not open {SOURCE_URL} with secret secret-value",
        },
        b"not-json",
        {"code": 0, "data": {}},
    ],
)
def test_start_sanitizes_nonzero_and_malformed_api_responses(response):
    client = make_zlm_client(FakeOpener(response))

    with pytest.raises(PreviewRelayError) as raised:
        client.start(stream_name="camera-1", source_url=SOURCE_URL)

    assert_sensitive_values_absent(raised.value)


def test_stop_rejects_nonzero_response_without_exposing_sensitive_values():
    response = {
        "code": -1,
        "msg": f"failed for admin:password at {SOURCE_URL}; secret=secret-value",
    }
    client = make_zlm_client(FakeOpener(response))

    with pytest.raises(PreviewRelayError) as raised:
        client.stop("source-key-1")

    assert_sensitive_values_absent(raised.value)


class FakePreviewClient:
    base_url = "http://zlm:82"

    def __init__(self, fail_starts=0):
        self.fail_starts = fail_starts
        self.started = []
        self.stopped = []

    def start(self, stream_name, source_url):
        self.started.append((stream_name, source_url))
        if self.fail_starts:
            self.fail_starts -= 1
            raise PreviewRelayError("preview relay start failed")
        return f"source-key-{len(self.started)}"

    def stop(self, key):
        self.stopped.append(key)


class FakeTimer:
    def __init__(self, delay, callback):
        self.delay = delay
        self.callback = callback
        self.daemon = False
        self.started = False
        self.cancelled = False

    def start(self):
        self.started = True

    def cancel(self):
        self.cancelled = True

    def fire(self):
        if not self.cancelled:
            self.callback()


class FakeTimerFactory:
    def __init__(self):
        self.timers = []

    def __call__(self, delay, callback):
        timer = FakeTimer(delay, callback)
        self.timers.append(timer)
        return timer


def make_manager(client=None, timers=None):
    client = client or FakePreviewClient()
    timers = timers or FakeTimerFactory()
    return (
        PreviewRelayManager(
            client=client,
            idle_seconds=60,
            timer_factory=timers,
        ),
        client,
        timers,
    )


def test_acquire_starts_once_and_shares_relay_between_viewers():
    manager, client, _ = make_manager()

    first_url = manager.acquire("camera-1", SOURCE_URL)
    second_url = manager.acquire("camera-1", SOURCE_URL)

    assert first_url == "http://zlm:82/live/preview-camera-1.live.flv"
    assert second_url == first_url
    assert client.started == [("camera-1", SOURCE_URL)]
    assert manager.viewer_count("camera-1") == 2


def test_releasing_last_viewer_starts_daemon_timer_and_expiry_stops_once():
    manager, client, timers = make_manager()
    manager.acquire("camera-1", SOURCE_URL)
    manager.acquire("camera-1", SOURCE_URL)

    manager.release("camera-1")
    assert timers.timers == []
    manager.release("camera-1")

    assert len(timers.timers) == 1
    timer = timers.timers[0]
    assert timer.delay == 60
    assert timer.daemon is True
    assert timer.started is True
    timer.fire()
    assert client.stopped == ["source-key-1"]


def test_reacquire_cancels_pending_idle_timer_and_reuses_relay():
    manager, client, timers = make_manager()
    manager.acquire("camera-1", SOURCE_URL)
    manager.release("camera-1")
    timer = timers.timers[0]

    relay_url = manager.acquire("camera-1", SOURCE_URL)

    assert relay_url == "http://zlm:82/live/preview-camera-1.live.flv"
    assert timer.cancelled is True
    assert client.started == [("camera-1", SOURCE_URL)]
    assert manager.viewer_count("camera-1") == 1
    timer.fire()
    assert client.stopped == []


def test_stop_stream_stops_managed_source_immediately_and_only_once():
    manager, client, _ = make_manager()
    manager.acquire("camera-1", SOURCE_URL)
    manager.acquire("camera-1", SOURCE_URL)

    manager.stop_stream("camera-1")
    manager.stop_stream("camera-1")

    assert client.stopped == ["source-key-1"]
    assert manager.viewer_count("camera-1") == 0


def test_shutdown_stops_every_managed_source_only_once():
    manager, client, timers = make_manager()
    manager.acquire("camera-1", SOURCE_URL)
    manager.acquire("camera-2", SOURCE_URL)
    manager.release("camera-1")
    pending_timer = timers.timers[0]

    manager.shutdown()
    manager.shutdown()
    pending_timer.fire()

    assert pending_timer.cancelled is True
    assert sorted(client.stopped) == ["source-key-1", "source-key-2"]
    assert manager.viewer_count("camera-1") == 0
    assert manager.viewer_count("camera-2") == 0


def test_failed_first_start_leaves_no_state_and_next_acquire_retries():
    client = FakePreviewClient(fail_starts=1)
    manager, _, _ = make_manager(client=client)

    with pytest.raises(PreviewRelayError):
        manager.acquire("camera-1", SOURCE_URL)

    assert manager.viewer_count("camera-1") == 0
    assert manager.acquire("camera-1", SOURCE_URL) == (
        "http://zlm:82/live/preview-camera-1.live.flv"
    )
    assert client.started == [
        ("camera-1", SOURCE_URL),
        ("camera-1", SOURCE_URL),
    ]
    assert manager.viewer_count("camera-1") == 1
