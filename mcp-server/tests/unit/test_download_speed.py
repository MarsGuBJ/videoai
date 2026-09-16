"""download_recording 的 speedx 参数校验与透传。"""

import asyncio

import pytest

from app import server
from app.tools.recordings import ALLOWED_DOWNLOAD_SPEEDS, normalize_download_speed


def test_normalize_download_speed_accepts_allowed_values():
    for value in ALLOWED_DOWNLOAD_SPEEDS:
        assert normalize_download_speed(value) == value
    assert ALLOWED_DOWNLOAD_SPEEDS == (1, 2, 4, 8, 16, 32)
    assert normalize_download_speed("16") == 16


@pytest.mark.parametrize("value", [0, 3, 5, 64, "abc", None])
def test_normalize_download_speed_rejects_invalid_values(value):
    with pytest.raises(ValueError, match="speedx must be one of"):
        normalize_download_speed(value)


def test_download_recording_rejects_invalid_speedx_before_resolving_nvr():
    """speedx 非法时先报错，不进入 NVR 解析/下载流程。"""
    with pytest.raises(ValueError, match="speedx must be one of"):
        asyncio.run(
            server.download_recording(
                nvr="10.10.7.252",
                startTime="2026-09-01T09:00:00",
                endTime="2026-09-01T09:05:00",
                speedx=3,
            )
        )
