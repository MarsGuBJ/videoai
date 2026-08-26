from app.media_proxy import MediaProxy


def make_proxy() -> MediaProxy:
    return MediaProxy(
        zlm_http_url="http://zlm",
        zlm_public_http_url="http://zlm",
        zlm_secret="secret",
        zlm_rtmp_push_base="rtmp://zlm/live",
        ttl_seconds=1800,
    )


def test_rtsp_ffmpeg_args_throttle_recording_playback_and_drop_audio():
    proxy = make_proxy()

    args = proxy._rtsp_ffmpeg_args("rec-demo", "rtsp://nvr/Streaming/tracks/601")

    assert args[:4] == ["ffmpeg", "-nostdin", "-loglevel", "error"]
    assert "-re" in args[: args.index("-i")]
    assert args[args.index("-i") + 1] == "rtsp://nvr/Streaming/tracks/601"
    assert "-an" in args
    assert args[args.index("-c:v") : args.index("-c:v") + 2] == ["-c:v", "copy"]
    assert args[-1] == "rtmp://zlm/live/rec-demo"


def test_file_ffmpeg_args_keep_realtime_pacing_and_drop_audio():
    proxy = make_proxy()

    args = proxy._file_ffmpeg_args("rec-demo", "/data/demo.ps")

    assert args[:4] == ["ffmpeg", "-nostdin", "-loglevel", "error"]
    assert "-re" in args[: args.index("-i")]
    assert args[args.index("-i") + 1] == "/data/demo.ps"
    assert "-an" in args
    assert args[args.index("-c:v") : args.index("-c:v") + 2] == ["-c:v", "copy"]
    assert args[-1] == "rtmp://zlm/live/rec-demo"
