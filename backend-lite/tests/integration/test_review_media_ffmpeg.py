"""复核视频抽帧的真实 ffmpeg 集成测试（配置的 ffmpeg 不可执行时跳过）。

单元测试用 mock 顶掉了 subprocess，发现不了"ffmpeg 实际读不到输入文件"这类环境问题。
历史故障：backend 的 FFMPEG_BIN 指向 chroot 到 /host 的 wrapper，容器内临时文件在被
chroot 的 ffmpeg 里不可见，视频判定固定返回 400；而把视频改从 stdin 管道喂入也不行，
因为 MP4 的 moov 索引默认在文件尾、不可 seek 的管道解析不了。故这里用**当前配置的**
ffmpeg 真实生成一段普通 MP4 并跑通抽帧。
"""

import shutil
import subprocess

import pytest

from app.services import review_media


def _configured_ffmpeg() -> str:
    """当前配置的 ffmpeg 可执行路径；不可用时跳过（不把环境缺失算作失败）。"""
    binary = review_media.get_settings().ffmpeg_bin
    resolved = shutil.which(binary)
    if not resolved:
        pytest.skip(f"ffmpeg 不可执行（FFMPEG_BIN={binary}），跳过真实抽帧测试")
    return resolved


def _make_plain_mp4(path, seconds: int = 6) -> bytes:
    """生成一个默认布局（moov 在文件尾）的 MP4，返回其字节。"""
    subprocess.run(
        [
            _configured_ffmpeg(),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc=duration={seconds}:size=320x240:rate=10",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        check=True,
    )
    return path.read_bytes()


def test_extract_video_frames_from_plain_mp4(tmp_path):
    """普通 MP4（moov 在文件尾）必须能抽出 JPEG 帧——纯管道方案正是在这里失败的。"""
    video_bytes = _make_plain_mp4(tmp_path / "plain.mp4")

    frames = review_media.extract_video_frames(video_bytes)

    assert frames, "普通 MP4 抽不出任何帧（检查 FFMPEG_BIN 是否指向容器内真实 ffmpeg）"
    assert all(frame.startswith(b"\xff\xd8") and frame.endswith(b"\xff\xd9") for frame in frames)
    assert all(len(frame) > 500 for frame in frames)
