"""流ID模式录像回放（现场 DS-A CVR）的单元测试：描述符构建、VOD 参数与下载拦截。"""

from datetime import datetime, timezone

from app.hcnetsdk_playback import (
    PlaybackSession,
    build_hcnetsdk_download_recording,
    build_hcnetsdk_recording,
    stable_recording_id,
)

BJT = timezone.utc
START = datetime(2026, 10, 9, 10, 0, 0, tzinfo=BJT)
END = datetime(2026, 10, 9, 10, 5, 0, tzinfo=BJT)
STREAM_ID = "405c14ed5fe147e7970485eecade27e3"


def make_session(stream_id: str = "") -> PlaybackSession:
    return PlaybackSession(
        sdk=None,  # VOD 参数构建不触 SDK
        stream_name="test-stream",
        host="172.19.200.21",
        port=8000,
        username="admin",
        password="secret",
        channel=3,
        start_time=START,
        end_time=END,
        rtmp_url="rtmp://zlm/live/test-stream",
        playback_url="http://zlm/live/test-stream.live.flv",
        timeout=15,
        expires_at=0,
        stream_id=stream_id,
    )


def test_build_recording_channel_mode_keeps_existing_shape():
    recording = build_hcnetsdk_recording("10.20.0.10", 8000, 3, START, END)

    assert recording.trackId == "3"
    assert recording.playbackUri == "hcnetsdk://10.20.0.10:8000/channels/3"
    assert recording.recordingId == stable_recording_id("10.20.0.10", 3, START, END)
    assert "streamId" not in recording.metadata


def test_build_recording_with_stream_id_uses_stream_in_identity():
    recording = build_hcnetsdk_recording("172.19.200.21", 8000, 0, START, END, stream_id=STREAM_ID)

    assert recording.trackId == STREAM_ID
    assert recording.playbackUri == f"hcnetsdk://172.19.200.21:8000/streams/{STREAM_ID}"
    assert recording.recordingId == stable_recording_id("172.19.200.21", STREAM_ID, START, END)
    assert recording.metadata["streamId"] == STREAM_ID


def test_build_download_recording_with_stream_id_uses_playback_capture():
    recording = build_hcnetsdk_download_recording("172.19.200.21", 8000, 0, START, END, stream_id=STREAM_ID)

    assert recording.trackId == STREAM_ID
    assert recording.metadata["streamId"] == STREAM_ID
    assert recording.metadata["downloadMode"] == "playback-capture"
    assert recording.playbackUri == f"hcnetsdk://172.19.200.21:8000/streams/{STREAM_ID}"


def test_vod_para_channel_mode_unchanged():
    vod = make_session()._vod_para()

    assert vod.struIDInfo.dwChannel == 3
    assert bytes(vod.struIDInfo.byID) == b"\x00" * 32
    assert vod.struBeginTime.dwYear == 2026 and vod.struBeginTime.dwHour == 10


def test_vod_para_stream_id_fills_by_id_and_zeroes_channel():
    vod = make_session(stream_id=STREAM_ID)._vod_para()

    assert bytes(vod.struIDInfo.byID) == STREAM_ID.encode()
    assert vod.struIDInfo.dwChannel == 0


def test_vod_para_stream_id_truncates_to_32_bytes():
    vod = make_session(stream_id="a" * 40)._vod_para()

    assert bytes(vod.struIDInfo.byID) == b"a" * 32


def test_ffmpeg_args_mp4_output_copies_stream_to_file():
    session = make_session(stream_id=STREAM_ID)
    session.mp4_output = "/tmp/out.mp4"

    args = session._ffmpeg_args()

    assert args[-1] == "/tmp/out.mp4"
    assert "-f" in args and "mpeg" in args
    assert args[args.index("-c:v") + 1] == "copy"
    assert "-an" in args
    assert "-movflags" in args and "+faststart" in args
    assert "-re" not in args and "-readrate" not in args
    assert "rtmp" not in " ".join(args)
