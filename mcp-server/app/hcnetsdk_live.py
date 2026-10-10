"""HCNetSDK 实时拉流降级链路：RTSP 不可用的海康设备经 SDK 取流推 ZLM。

部分海康设备（现场为 DS-2TD 系列热成像相机）RTSP 服务直接重置连接，但 SDK 8000
端口工作正常。本模块为该场景提供与常规 RTSP 拉流等价的播放链路：

平台 backend-media 开播被拒绝（ZLM addStreamProxy 失败）时调用
``POST /live-pull/start``（见 ``app.routes``），此处登录设备并
``NET_DVR_RealPlay_V40`` 实时取流（回调收 MPEG-PS，type=1 的 IMKH 私有头丢弃），
经 ffmpeg 统一转码 H.264 推 RTMP 到 ZLM ``app=live stream=<streamName>``。
不区分设备原编码做 copy/skip：起流嗅探在热成像相机上实测把 H.265 误判为 H.264
（与回放链路修过的 0x27 头字节歧义同源），统一转码输出与现场其余摄像头一致、
播放器兼容有保证；热成像相机预览并发量小，转码开销可接受。
前端播放地址（ZLM FLV）与常规拉流完全一致。

会话生命周期：ZLM 无观众自动断开发布者 → ffmpeg 退出 → 看护线程回收 SDK 会话；
无人观看即释放设备连接，与平台守护线程对 RUNNING 设备重挂代理失败后置 STOPPED
的语义一致。
"""

from __future__ import annotations

import asyncio
import logging
import queue
import subprocess
import threading
import time
from contextlib import suppress
from ctypes import (
    CFUNCTYPE,
    POINTER,
    Structure,
    byref,
    c_bool,
    c_byte,
    c_long,
    c_uint32,
    c_ulong,
    c_void_p,
    string_at,
)
from dataclasses import dataclass, field
from typing import Any

import httpx

from .hcnetsdk_playback import (
    HcNetSdkError,
    HcNetSdkLibrary,
)

logger = logging.getLogger(__name__)

# 实时流回调数据类型：NET_DVR_SYSHEAD(1) 为 IMKH 私有头，NET_DVR_STREAMDATA(2) 为 PS 数据
NET_DVR_SYSHEAD = 1
NET_DVR_STREAMDATA = 2
REALPLAY_CALLBACK = CFUNCTYPE(None, c_long, c_uint32, POINTER(c_byte), c_uint32, c_void_p)

LIVE_QUEUE_MAXSIZE = 512
# 会话空闲（无 SDK 数据）超过该时长判定设备断流，主动结束会话
LIVE_IDLE_TIMEOUT_SECONDS = 30


class NET_DVR_PREVIEWINFO(Structure):
    _fields_ = [
        ("lChannel", c_long),
        ("dwStreamType", c_ulong),
        ("dwLinkMode", c_ulong),
        ("hPlayWnd", c_void_p),
        ("bBlocked", c_ulong),
        ("bPassbackRecord", c_ulong),
        ("byPreviewMode", c_byte),
        ("byStreamID", c_byte * 32),
        ("byProtoType", c_byte),
        ("byRes1", c_byte),
        ("dwDisplayBufNum", c_ulong),
        ("byRes", c_byte * 216),
    ]


def _ensure_realplay_prototypes(sdk: HcNetSdkLibrary) -> None:
    """为共享 SDK 句柄补充实时预览相关函数原型（幂等）。"""
    if getattr(sdk, "_live_prototypes_ready", False):
        return
    sdk.sdk.NET_DVR_RealPlay_V40.argtypes = [c_long, POINTER(NET_DVR_PREVIEWINFO), REALPLAY_CALLBACK, c_void_p]
    sdk.sdk.NET_DVR_RealPlay_V40.restype = c_long
    sdk.sdk.NET_DVR_StopRealPlay.argtypes = [c_long]
    sdk.sdk.NET_DVR_StopRealPlay.restype = c_bool
    sdk._live_prototypes_ready = True


@dataclass
class LivePullSession:
    """一台设备的 SDK 实时拉流会话：RealPlay → ffmpeg → RTMP 推 ZLM。"""

    sdk: HcNetSdkLibrary
    stream_name: str
    host: str
    port: int
    username: str
    password: str
    stream_type: str
    rtmp_url: str
    timeout: float
    user_id: int = -1
    real_handle: int = -1
    callback: Any = None
    queue: queue.Queue[bytes | None] = field(default_factory=lambda: queue.Queue(maxsize=LIVE_QUEUE_MAXSIZE))
    writer: threading.Thread | None = None
    failed: str = ""
    last_data_at: float = 0.0
    _stopped: bool = False

    def start(self) -> None:
        """登录设备并起实时预览；SDK 回调线程开始收 PS 数据。"""
        _ensure_realplay_prototypes(self.sdk)
        self.sdk.sdk.NET_DVR_SetConnectTime(int(self.timeout * 1000), 1)
        self.sdk.sdk.NET_DVR_SetReconnect(10000, True)
        self.user_id = self.sdk.login(self.host, self.port, self.username, self.password)
        info = NET_DVR_PREVIEWINFO()
        info.lChannel = 1
        info.dwStreamType = 1 if self.stream_type == "sub" else 0
        info.dwLinkMode = 0  # TCP
        self.callback = REALPLAY_CALLBACK(self._on_real_data)
        handle = int(self.sdk.sdk.NET_DVR_RealPlay_V40(self.user_id, byref(info), self.callback, None))
        if handle < 0:
            raise HcNetSdkError(f"NET_DVR_RealPlay_V40 failed: {self.sdk.last_error()}")
        self.real_handle = handle
        self.writer = threading.Thread(target=self._writer_main, name=f"live-pull-{self.stream_name}", daemon=True)
        self.writer.start()

    def stop(self) -> None:
        """停 SDK 预览并回收 ffmpeg；幂等。"""
        self._stopped = True
        if self.real_handle >= 0:
            with suppress(Exception):
                self.sdk.sdk.NET_DVR_StopRealPlay(self.real_handle)
            self.real_handle = -1
        self.queue_put(None)
        if self.writer is not None:
            self.writer.join(timeout=5)
            self.writer = None
        if self.user_id >= 0:
            with suppress(Exception):
                self.sdk.sdk.NET_DVR_Logout(self.user_id)
            self.user_id = -1

    def _on_real_data(self, handle: int, data_type: int, buffer: Any, size: int, user: Any) -> None:
        if size <= 0 or not buffer:
            return
        self.last_data_at = time.monotonic()
        if data_type != NET_DVR_STREAMDATA:
            # IMKH 私有头（type=1）对 PS 解复用无意义，直接丢弃
            return
        self.queue_put(string_at(buffer, int(size)))

    def queue_put(self, item: bytes | None) -> None:
        """实时流无法像回放那样暂停设备供流：队列满时丢包计数（持续拥塞由空闲看护结束会话）。"""
        try:
            self.queue.put_nowait(item)
        except queue.Full:
            if item is not None:
                self._dropped = getattr(self, "_dropped", 0) + 1
                if self._dropped % 100 == 1:
                    logger.warning("live-pull %s queue full, dropped %d packets", self.stream_name, self._dropped)

    def _writer_main(self) -> None:
        """拉起 ffmpeg 转码推流 → 泵队列，退出即会话结束。"""
        ffmpeg: subprocess.Popen[bytes] | None = None
        try:
            ffmpeg = subprocess.Popen(  # noqa: S603
                self._ffmpeg_args(),  # noqa: S607
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            stdin = ffmpeg.stdin
            assert stdin is not None
            self._pump(stdin, ffmpeg)
        except Exception as exc:  # noqa: BLE001  # 会话失败原因透传给 start 调用方
            if not self._stopped:
                self.failed = f"{type(exc).__name__}: {exc}"
                logger.warning("live-pull %s writer ended with error: %s", self.stream_name, self.failed)
        finally:
            self._reap_ffmpeg(ffmpeg)

    def _pump(self, stdin: Any, ffmpeg: subprocess.Popen[bytes]) -> None:
        """持续把队列中的 PS 数据写入 ffmpeg；空闲超时或进程退出即结束。"""
        while not self._stopped:
            if ffmpeg.poll() is not None:
                raise HcNetSdkError(f"ffmpeg exited early: rc={ffmpeg.returncode}")
            try:
                item = self.queue.get(timeout=1)
            except queue.Empty:
                if self.last_data_at and time.monotonic() - self.last_data_at > LIVE_IDLE_TIMEOUT_SECONDS:
                    raise HcNetSdkError("no stream data within idle timeout")
                continue
            if item is None:
                break
            stdin.write(item)
        stdin.flush()

    def _ffmpeg_args(self) -> list[str]:
        # 统一转码 H.264：与回放链路同一套参数（smart265/HEVC 及异常 H.264 头字节
        # 均可安全解码），输出 FLV 播放器兼容性与现场其余摄像头一致
        return [
            "ffmpeg",
            "-nostdin",
            "-loglevel",
            "error",
            "-fflags",
            "nobuffer",
            "-f",
            "mpeg",
            "-probesize",
            "1000000",
            "-analyzeduration",
            "1000000",
            "-i",
            "pipe:0",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-tune",
            "zerolatency",
            "-pix_fmt",
            "yuv420p",
            "-g",
            "50",
            "-f",
            "flv",
            self.rtmp_url,
        ]

    def _reap_ffmpeg(self, ffmpeg: subprocess.Popen[bytes] | None) -> None:
        if ffmpeg is None:
            return
        if ffmpeg.stdin is not None and not ffmpeg.stdin.closed:
            with suppress(BrokenPipeError, OSError, ValueError):
                ffmpeg.stdin.close()
        try:
            ffmpeg.wait(timeout=5)
        except subprocess.TimeoutExpired:
            ffmpeg.kill()
            with suppress(Exception):
                ffmpeg.wait(timeout=5)


class LivePullManager:
    """按 streamName 管理实时拉流会话；同一流幂等复用。"""

    def __init__(
        self,
        zlm_http_url: str,
        zlm_secret: str,
        zlm_rtmp_push_base: str,
        timeout: float = 20,
    ) -> None:
        self.zlm_http_url = zlm_http_url.rstrip("/")
        self.zlm_secret = zlm_secret
        self.zlm_rtmp_push_base = zlm_rtmp_push_base.rstrip("/")
        self.timeout = timeout
        self._sessions: dict[str, LivePullSession] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    async def _lock_for(self, stream_name: str) -> asyncio.Lock:
        async with self._guard:
            return self._locks.setdefault(stream_name, asyncio.Lock())

    async def start(
        self,
        stream_name: str,
        host: str,
        port: int,
        username: str,
        password: str,
        stream_type: str = "main",
    ) -> LivePullSession:
        """建立（或复用）一路实时拉流，等待 ZLM 上可见后返回。"""
        lock = await self._lock_for(stream_name)
        async with lock:
            session = self._sessions.get(stream_name)
            if session is not None and not session.failed and session.real_handle >= 0:
                return session
            if session is not None:
                # 旧会话已失效（ffmpeg 退出/设备断流）：先回收再重拉，避免泄漏 SDK 连接
                self._sessions.pop(stream_name, None)
                await asyncio.to_thread(session.stop)
            session = LivePullSession(
                sdk=HcNetSdkLibrary.instance(),
                stream_name=stream_name,
                host=host,
                port=port,
                username=username,
                password=password,
                stream_type=stream_type,
                rtmp_url=f"{self.zlm_rtmp_push_base}/{stream_name}",
                timeout=self.timeout,
            )
            try:
                await asyncio.to_thread(session.start)
                await asyncio.to_thread(self._wait_until_stream_ready, session)
            except Exception:
                await asyncio.to_thread(session.stop)
                self._sessions.pop(stream_name, None)
                raise
            self._sessions[stream_name] = session
            self._watch(session)
            logger.info("live-pull started for %s (%s:%d, %s)", stream_name, host, port, stream_type)
            return session

    async def stop(self, stream_name: str) -> None:
        lock = await self._lock_for(stream_name)
        async with lock:
            session = self._sessions.pop(stream_name, None)
            if session is not None:
                await asyncio.to_thread(session.stop)

    def _watch(self, session: LivePullSession) -> None:
        """看护线程：ffmpeg 退出（ZLM 无观众断开/设备断流）即回收 SDK 会话。"""

        def watch() -> None:
            writer = session.writer
            if writer is not None:
                writer.join()
            if not session.failed and session.real_handle >= 0:
                session.failed = "ffmpeg writer ended"
            if self._sessions.get(session.stream_name) is session:
                self._sessions.pop(session.stream_name, None)
            with suppress(Exception):
                session.stop()
            logger.info("live-pull ended for %s", session.stream_name)

        threading.Thread(target=watch, name=f"live-pull-watch-{session.stream_name}", daemon=True).start()

    def _wait_until_stream_ready(self, session: LivePullSession) -> None:
        deadline = time.monotonic() + min(max(self.timeout, 10), 30)
        while time.monotonic() < deadline:
            if session.failed:
                raise HcNetSdkError(session.failed)
            if self._stream_exists(session.stream_name):
                return
            time.sleep(0.25)
        raise TimeoutError(f"live-pull stream was not ready on ZLM: {session.stream_name}")

    def _stream_exists(self, stream_name: str) -> bool:
        try:
            with httpx.Client(timeout=min(self.timeout, 5)) as client:
                response = client.get(
                    f"{self.zlm_http_url}/index/api/getMediaList",
                    params={"secret": self.zlm_secret},
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError):
            return False
        if payload.get("code") != 0:
            return False
        return any(item.get("stream") == stream_name for item in payload.get("data") or [])
