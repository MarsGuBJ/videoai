"""mp4_compat：HEVC 探测与 H.264 转码参数。"""

from __future__ import annotations

import json
import subprocess

from app import mp4_compat
from app.mp4_compat import ensure_browser_compatible_mp4, h264_compatible_video_args, probe_video_codec


def _fake_completed(payload: dict, returncode: int = 0):
    return subprocess.CompletedProcess([], returncode, json.dumps(payload), "")


def test_probe_video_codec_reads_first_stream(monkeypatch, tmp_path):
    monkeypatch.setattr(
        mp4_compat.subprocess,
        "run",
        lambda *a, **k: _fake_completed({"streams": [{"codec_name": "hevc"}]}),
    )
    assert probe_video_codec(tmp_path / "a.mp4") == "hevc"


def test_probe_video_codec_returns_empty_on_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(mp4_compat.subprocess, "run", lambda *a, **k: _fake_completed({}, returncode=1))
    assert probe_video_codec(tmp_path / "a.mp4") == ""


def test_h264_compatible_video_args_transcodes_hevc():
    args = h264_compatible_video_args("hevc")
    assert "libx264" in args
    assert "yuv420p" in args


def test_h264_compatible_video_args_copies_h264():
    assert h264_compatible_video_args("h264") == ["-c:v", "copy"]


def test_ensure_browser_compatible_mp4_keeps_h264(monkeypatch, tmp_path):
    mp4 = tmp_path / "a.mp4"
    mp4.write_bytes(b"x")
    monkeypatch.setattr(mp4_compat, "probe_video_codec", lambda f: "h264")
    assert ensure_browser_compatible_mp4(mp4) == mp4


def test_ensure_browser_compatible_mp4_transcodes_hevc_in_place(monkeypatch, tmp_path):
    mp4 = tmp_path / "a.mp4"
    mp4.write_bytes(b"hevc")
    monkeypatch.setattr(mp4_compat, "probe_video_codec", lambda f: "hevc")

    def fake_run(cmd, **kwargs):
        # 模拟 ffmpeg 产出转码结果文件
        tmp_path.joinpath("a.h264.mp4").write_bytes(b"h264")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(mp4_compat.subprocess, "run", fake_run)
    assert ensure_browser_compatible_mp4(mp4) == mp4
    assert mp4.read_bytes() == b"h264"
    assert not (tmp_path / "a.h264.mp4").exists()
