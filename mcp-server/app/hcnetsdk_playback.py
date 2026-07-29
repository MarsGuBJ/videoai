from __future__ import annotations

import asyncio
from ctypes import (
    CFUNCTYPE,
    POINTER,
    Structure,
    byref,
    c_bool,
    c_char,
    c_char_p,
    c_int,
    c_long,
    c_ubyte,
    c_uint16,
    c_uint32,
    c_void_p,
    create_string_buffer,
    sizeof,
    string_at,
)
import ctypes
from dataclasses import dataclass
from datetime import datetime
import hashlib
import importlib.util
from pathlib import Path
import queue
import shutil
import subprocess
import tempfile
import threading
import time
from typing import Any
from uuid import uuid4

import httpx

from .models import RecordingSegment


NET_DVR_PLAYSTART = 1
NET_DVR_PLAYBACK_BY_TIME = "hikvision_hcnetsdk_playback"
NET_DVR_DOWNLOAD_BY_TIME = "hikvision_hcnetsdk_download"
PLAYBACK_CALLBACK = CFUNCTYPE(None, c_long, c_uint32, POINTER(c_ubyte), c_uint32, c_void_p)


class HcNetSdkError(RuntimeError):
    pass


class NET_DVR_TIME(Structure):
    _fields_ = [
        ("dwYear", c_uint32),
        ("dwMonth", c_uint32),
        ("dwDay", c_uint32),
        ("dwHour", c_uint32),
        ("dwMinute", c_uint32),
        ("dwSecond", c_uint32),
    ]


class NET_DVR_STREAM_INFO(Structure):
    _fields_ = [
        ("dwSize", c_uint32),
        ("byID", c_ubyte * 32),
        ("dwChannel", c_uint32),
        ("byRes", c_ubyte * 32),
    ]


class NET_DVR_VOD_PARA(Structure):
    _fields_ = [
        ("dwSize", c_uint32),
        ("struIDInfo", NET_DVR_STREAM_INFO),
        ("struBeginTime", NET_DVR_TIME),
        ("struEndTime", NET_DVR_TIME),
        ("hWnd", c_void_p),
        ("byDrawFrame", c_ubyte),
        ("byRes", c_ubyte * 31),
    ]


class NET_DVR_LOCAL_SDK_PATH(Structure):
    _fields_ = [
        ("sPath", c_char * 256),
        ("byRes", c_ubyte * 128),
    ]


class NET_DVR_DEVICEINFO_V30(Structure):
    _fields_ = [
        ("sSerialNumber", c_ubyte * 48),
        ("byAlarmInPortNum", c_ubyte),
        ("byAlarmOutPortNum", c_ubyte),
        ("byDiskNum", c_ubyte),
        ("byDVRType", c_ubyte),
        ("byChanNum", c_ubyte),
        ("byStartChan", c_ubyte),
        ("byAudioChanNum", c_ubyte),
        ("byIPChanNum", c_ubyte),
        ("byZeroChanNum", c_ubyte),
        ("byMainProto", c_ubyte),
        ("bySubProto", c_ubyte),
        ("bySupport", c_ubyte),
        ("bySupport1", c_ubyte),
        ("bySupport2", c_ubyte),
        ("wDevType", c_uint16),
        ("bySupport3", c_ubyte),
        ("byMultiStreamProto", c_ubyte),
        ("byStartDChan", c_ubyte),
        ("byStartDTalkChan", c_ubyte),
        ("byHighDChanNum", c_ubyte),
        ("bySupport4", c_ubyte),
        ("byLanguageType", c_ubyte),
        ("byVoiceInChanNum", c_ubyte),
        ("byStartVoiceInChanNo", c_ubyte),
        ("byRes3", c_ubyte * 2),
        ("byMirrorChanNum", c_ubyte),
        ("wStartMirrorChanNo", c_uint16),
        ("byRes2", c_ubyte * 2),
        ("byRes", c_ubyte * 172),
    ]


class NET_DVR_DEVICEINFO_V40(Structure):
    _fields_ = [
        ("struDeviceV30", NET_DVR_DEVICEINFO_V30),
        ("byRes", c_ubyte * 256),
    ]


LOGIN_CALLBACK = CFUNCTYPE(None, c_uint32, c_uint32, POINTER(NET_DVR_DEVICEINFO_V40), c_void_p)


class NET_DVR_USER_LOGIN_INFO(Structure):
    _fields_ = [
        ("sDeviceAddress", c_char * 129),
        ("byUseTransport", c_ubyte),
        ("wPort", c_uint16),
        ("sUserName", c_char * 64),
        ("sPassword", c_char * 64),
        ("cbLoginResult", LOGIN_CALLBACK),
        ("pUser", c_void_p),
        ("bUseAsynLogin", c_uint32),
        ("byProxyType", c_ubyte),
        ("byUseUTCTime", c_ubyte),
        ("byLoginMode", c_ubyte),
        ("byHttps", c_ubyte),
        ("iProxyID", c_uint32),
        ("byVerifyMode", c_ubyte),
        ("byRes2", c_ubyte * 119),
    ]


def build_hcnetsdk_recording(
    host: str,
    port: int,
    channel: int,
    start_time: datetime,
    end_time: datetime,
) -> RecordingSegment:
    playback_uri = f"hcnetsdk://{host}:{port}/channels/{channel}"
    recording_id = stable_recording_id(host, channel, start_time, end_time)
    return RecordingSegment(
        recordingId=recording_id,
        cameraId=f"{host}-channel-{channel}",
        cameraName=f"IPC-{host}-{channel}",
        trackId=str(channel),
        startTime=start_time,
        endTime=end_time,
        playbackUri=playback_uri,
        source=NET_DVR_PLAYBACK_BY_TIME,
        metadata={
            "deviceHost": host,
            "devicePort": port,
            "channel": channel,
            "protocol": "HCNetSDK",
            "sdkApi": "NET_DVR_PlayBackByTime_V40",
        },
    )


def build_hcnetsdk_download_recording(
    host: str,
    port: int,
    channel: int,
    start_time: datetime,
    end_time: datetime,
) -> RecordingSegment:
    recording = build_hcnetsdk_recording(host, port, channel, start_time, end_time)
    recording.source = NET_DVR_DOWNLOAD_BY_TIME
    recording.metadata["sdkApi"] = "NET_DVR_GetFileByTime"
    return recording


def stable_recording_id(host: str, channel: int, start_time: datetime, end_time: datetime) -> str:
    digest = hashlib.sha256(f"{host}|{channel}|{start_time.isoformat()}|{end_time.isoformat()}".encode()).hexdigest()
    return digest[:32]


def device_channel_numbers(
    start_channel: int,
    analog_count: int,
    start_digital_channel: int,
    digital_count: int,
) -> list[int]:
    analog = range(start_channel, start_channel + analog_count) if analog_count > 0 else ()
    digital = range(start_digital_channel, start_digital_channel + digital_count) if digital_count > 0 else ()
    return sorted(set(analog) | set(digital))


def channels_from_device_info(device_info: NET_DVR_DEVICEINFO_V40) -> list[int]:
    info = device_info.struDeviceV30
    digital_count = int(info.byIPChanNum) + (int(info.byHighDChanNum) << 8)
    return device_channel_numbers(
        start_channel=int(info.byStartChan),
        analog_count=int(info.byChanNum),
        start_digital_channel=int(info.byStartDChan),
        digital_count=digital_count,
    )


def to_sdk_time(value: datetime) -> NET_DVR_TIME:
    return NET_DVR_TIME(
        value.year,
        value.month,
        value.day,
        value.hour,
        value.minute,
        value.second,
    )


class HcNetSdkPlaybackProxy:
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        channel: int,
        zlm_http_url: str,
        zlm_public_http_url: str,
        zlm_secret: str,
        zlm_rtmp_push_base: str,
        ttl_seconds: int,
        timeout: float = 15,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.channel = channel
        self.zlm_http_url = zlm_http_url.rstrip("/")
        self.zlm_public_http_url = zlm_public_http_url.rstrip("/")
        self.zlm_secret = zlm_secret
        self.zlm_rtmp_push_base = zlm_rtmp_push_base.rstrip("/")
        self.ttl_seconds = ttl_seconds
        self.timeout = timeout
        self._semaphore = asyncio.Semaphore(1)
        self._sessions: dict[str, PlaybackSession] = {}
        self._max_live_sessions_before_reset = 2

    def build_recording(self, start_time: datetime, end_time: datetime) -> RecordingSegment:
        return build_hcnetsdk_recording(self.host, self.port, self.channel, start_time, end_time)

    def build_download_recording(self, start_time: datetime, end_time: datetime) -> RecordingSegment:
        return build_hcnetsdk_download_recording(self.host, self.port, self.channel, start_time, end_time)

    async def start_playback(self, recording: RecordingSegment) -> str:
        async with self._semaphore:
            await self._cleanup_expired_locked()
            if len(self._sessions) >= self._max_live_sessions_before_reset:
                await self._stop_all_locked()
            session = await asyncio.to_thread(self._start_session, recording)
            self._sessions[session.stream_name] = session
            return session.playback_url

    async def stop_playback(self) -> None:
        async with self._semaphore:
            await self._stop_all_locked()

    async def _stop_all_locked(self) -> None:
        if not self._sessions:
            return
        sessions = list(self._sessions.values())
        self._sessions.clear()
        for session in sessions:
            await asyncio.to_thread(self._stop_session, session)

    async def _cleanup_expired_locked(self) -> None:
        now = time.monotonic()
        expired = [
            stream_name
            for stream_name, session in self._sessions.items()
            if session.expires_at <= now or session.ffmpeg.poll() is not None or session.failed
        ]
        for stream_name in expired:
            session = self._sessions.pop(stream_name)
            await asyncio.to_thread(self._stop_session, session)

    def _start_session(self, recording: RecordingSegment) -> "PlaybackSession":
        stream_name = f"hcn-{recording.recordingId[:12]}-{uuid4().hex[:8]}"
        playback_url = f"{self.zlm_public_http_url}/live/{stream_name}.live.flv"
        self._close_zlm_stream(stream_name)
        session = PlaybackSession(
            sdk=HcNetSdkLibrary.instance(),
            stream_name=stream_name,
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            channel=self.channel,
            start_time=recording.startTime,
            end_time=recording.endTime,
            rtmp_url=f"{self.zlm_rtmp_push_base}/{stream_name}",
            playback_url=playback_url,
            timeout=self.timeout,
            expires_at=time.monotonic() + max(self.ttl_seconds, 1),
        )
        try:
            session.start()
            self._wait_until_stream_ready(stream_name, session)
        except Exception:
            session.stop()
            raise
        return session

    def _stop_session(self, session: "PlaybackSession") -> None:
        session.stop()
        self._close_zlm_stream(session.stream_name)

    async def download_mp4(self, recording: RecordingSegment) -> Path:
        return await asyncio.to_thread(self._download_mp4, recording)

    def _download_mp4(self, recording: RecordingSegment) -> Path:
        work_dir = Path(tempfile.mkdtemp(prefix="hcnetsdk-download-"))
        ps_file = work_dir / f"{recording.recordingId}.ps"
        mp4_file = work_dir / f"{recording.recordingId}.mp4"
        sdk = None
        user_id = -1
        download_handle = -1
        try:
            sdk = HcNetSdkLibrary.instance()
            sdk.sdk.NET_DVR_SetConnectTime(int(self.timeout * 1000), 1)
            sdk.sdk.NET_DVR_SetReconnect(10000, True)
            user_id = sdk.login(self.host, self.port, self.username, self.password)
            download_handle = int(
                sdk.sdk.NET_DVR_GetFileByTime(
                    user_id,
                    self.channel,
                    byref(to_sdk_time(recording.startTime)),
                    byref(to_sdk_time(recording.endTime)),
                    str(ps_file).encode(),
                )
            )
            if download_handle < 0:
                raise HcNetSdkError(f"NET_DVR_GetFileByTime failed: {sdk.last_error()}")
            if not sdk.sdk.NET_DVR_PlayBackControl(download_handle, NET_DVR_PLAYSTART, 0, None):
                raise HcNetSdkError(f"NET_DVR_PlayBackControl download start failed: {sdk.last_error()}")
            self._wait_until_downloaded(sdk, download_handle, recording)
            self._remux_to_mp4(ps_file, mp4_file)
            final_file = Path(tempfile.gettempdir()) / f"{recording.recordingId}.mp4"
            shutil.move(str(mp4_file), final_file)
            return final_file
        finally:
            if sdk is not None and download_handle >= 0:
                sdk.sdk.NET_DVR_StopGetFile(download_handle)
            if sdk is not None and user_id >= 0:
                sdk.sdk.NET_DVR_Logout(user_id)
            shutil.rmtree(work_dir, ignore_errors=True)

    def _wait_until_downloaded(self, sdk: "HcNetSdkLibrary", download_handle: int, recording: RecordingSegment) -> None:
        duration_seconds = max((recording.endTime - recording.startTime).total_seconds(), 1)
        deadline = time.monotonic() + max(self.timeout, min(duration_seconds * 3 + 60, 3600))
        last_pos = -1
        idle_ticks = 0
        while time.monotonic() < deadline:
            pos = int(sdk.sdk.NET_DVR_GetDownloadPos(download_handle))
            if pos >= 100:
                return
            if pos < 0:
                raise HcNetSdkError(f"NET_DVR_GetDownloadPos failed: {sdk.last_error()}")
            if pos == last_pos:
                idle_ticks += 1
            else:
                idle_ticks = 0
                last_pos = pos
            if idle_ticks >= 60:
                raise TimeoutError(f"HCNetSDK download stalled at {pos}%")
            time.sleep(1)
        raise TimeoutError("HCNetSDK download timed out")

    def _remux_to_mp4(self, source_file: Path, mp4_file: Path) -> None:
        result = subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(source_file),
                "-an",
                "-c:v",
                "copy",
                "-movflags",
                "+faststart",
                str(mp4_file),
            ],
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or f"ffmpeg exited with code {result.returncode}"
            raise HcNetSdkError(f"ffmpeg remux to MP4 failed: {detail}")

    def _wait_until_stream_ready(self, stream_name: str, session: "PlaybackSession") -> None:
        deadline = time.monotonic() + min(max(self.timeout, 5), 30)
        while time.monotonic() < deadline:
            if session.failed:
                raise HcNetSdkError(session.failed)
            if session.ffmpeg.poll() is not None:
                raise HcNetSdkError(session.ffmpeg_error())
            if self._stream_exists(stream_name):
                return
            time.sleep(0.25)
        raise TimeoutError(f"HCNetSDK playback stream was not ready: {stream_name}")

    def _stream_exists(self, stream_name: str) -> bool:
        try:
            with httpx.Client(timeout=min(self.timeout, 5)) as client:
                response = client.get(
                    f"{self.zlm_http_url}/index/api/getMediaList",
                    params={"secret": self.zlm_secret},
                )
                response.raise_for_status()
                payload = response.json()
        except Exception:
            return False
        if payload.get("code") != 0:
            return False
        return any(item.get("stream") == stream_name for item in payload.get("data") or [])

    def _close_zlm_stream(self, stream_name: str) -> None:
        try:
            with httpx.Client(timeout=min(self.timeout, 5)) as client:
                client.get(
                    f"{self.zlm_http_url}/index/api/close_streams",
                    params={
                        "secret": self.zlm_secret,
                        "vhost": "__defaultVhost__",
                        "app": "live",
                        "stream": stream_name,
                        "force": "1",
                    },
                )
        except Exception:
            pass


@dataclass(frozen=True)
class HcNetSdkDeviceSession:
    user_id: int
    channels: tuple[int, ...]


class HcNetSdkLibrary:
    _instance: "HcNetSdkLibrary | None" = None
    _lock = threading.Lock()

    @classmethod
    def instance(cls) -> "HcNetSdkLibrary":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self) -> None:
        self.lib_dir = self._find_lib_dir()
        self.sdk = self._load_sdk()
        self._configure_prototypes()
        self._set_init_cfg()
        if not self.sdk.NET_DVR_Init():
            raise HcNetSdkError(f"NET_DVR_Init failed: {self.last_error()}")

    def _find_lib_dir(self) -> Path:
        spec = importlib.util.find_spec("HCNetSDK")
        if spec is None or not spec.submodule_search_locations:
            raise HcNetSdkError("hcnetsdk-python package is not installed")
        lib_dir = Path(next(iter(spec.submodule_search_locations))) / "Libs" / "linux"
        if not (lib_dir / "libhcnetsdk.so").is_file():
            raise HcNetSdkError(f"libhcnetsdk.so was not found under {lib_dir}")
        return lib_dir

    def _load_sdk(self) -> Any:
        sdk_com_dir = self.lib_dir / "HCNetSDKCom"
        preload = [
            "libcrypto.so.1.1",
            "libssl.so.1.1",
            "libz.so",
            "libhpr.so",
            "libHCCore.so",
            "libNPQos.so",
            "libPlayCtrl.so",
        ]
        for name in preload:
            path = self.lib_dir / name
            if path.exists():
                ctypes.CDLL(str(path), mode=ctypes.RTLD_GLOBAL)
        if sdk_com_dir.is_dir():
            for path in sorted(sdk_com_dir.glob("*.so")):
                ctypes.CDLL(str(path), mode=ctypes.RTLD_GLOBAL)
        return ctypes.CDLL(str(self.lib_dir / "libhcnetsdk.so"), mode=ctypes.RTLD_GLOBAL)

    def _configure_prototypes(self) -> None:
        self.sdk.NET_DVR_Init.restype = c_bool
        self.sdk.NET_DVR_SetSDKInitCfg.argtypes = [c_uint32, c_void_p]
        self.sdk.NET_DVR_SetSDKInitCfg.restype = c_bool
        self.sdk.NET_DVR_GetLastError.restype = c_uint32
        self.sdk.NET_DVR_SetConnectTime.argtypes = [c_uint32, c_uint32]
        self.sdk.NET_DVR_SetConnectTime.restype = c_bool
        self.sdk.NET_DVR_SetReconnect.argtypes = [c_uint32, c_bool]
        self.sdk.NET_DVR_SetReconnect.restype = c_bool
        self.sdk.NET_DVR_Login_V40.argtypes = [POINTER(NET_DVR_USER_LOGIN_INFO), POINTER(NET_DVR_DEVICEINFO_V40)]
        self.sdk.NET_DVR_Login_V40.restype = c_long
        self.sdk.NET_DVR_Logout.argtypes = [c_long]
        self.sdk.NET_DVR_Logout.restype = c_bool
        self.sdk.NET_DVR_PlayBackByTime_V40.argtypes = [c_long, POINTER(NET_DVR_VOD_PARA)]
        self.sdk.NET_DVR_PlayBackByTime_V40.restype = c_long
        self.sdk.NET_DVR_SetPlayDataCallBack_V40.argtypes = [c_long, PLAYBACK_CALLBACK, c_void_p]
        self.sdk.NET_DVR_SetPlayDataCallBack_V40.restype = c_bool
        self.sdk.NET_DVR_PlayBackControl_V40.argtypes = [c_long, c_uint32, c_void_p, c_uint32, c_void_p, POINTER(c_uint32)]
        self.sdk.NET_DVR_PlayBackControl_V40.restype = c_bool
        self.sdk.NET_DVR_StopPlayBack.argtypes = [c_long]
        self.sdk.NET_DVR_StopPlayBack.restype = c_bool
        self.sdk.NET_DVR_GetFileByTime.argtypes = [c_long, c_long, POINTER(NET_DVR_TIME), POINTER(NET_DVR_TIME), c_char_p]
        self.sdk.NET_DVR_GetFileByTime.restype = c_long
        self.sdk.NET_DVR_PlayBackControl.argtypes = [c_long, c_uint32, c_uint32, c_void_p]
        self.sdk.NET_DVR_PlayBackControl.restype = c_bool
        self.sdk.NET_DVR_GetDownloadPos.argtypes = [c_long]
        self.sdk.NET_DVR_GetDownloadPos.restype = c_int
        self.sdk.NET_DVR_StopGetFile.argtypes = [c_long]
        self.sdk.NET_DVR_StopGetFile.restype = c_bool

    def _set_init_cfg(self) -> None:
        sdk_path = NET_DVR_LOCAL_SDK_PATH()
        sdk_path.sPath = str(self.lib_dir).encode()
        self.sdk.NET_DVR_SetSDKInitCfg(2, byref(sdk_path))
        self.sdk.NET_DVR_SetSDKInitCfg(3, create_string_buffer(str(self.lib_dir / "libcrypto.so.1.1").encode()))
        self.sdk.NET_DVR_SetSDKInitCfg(4, create_string_buffer(str(self.lib_dir / "libssl.so.1.1").encode()))

    def last_error(self) -> int:
        return int(self.sdk.NET_DVR_GetLastError())

    def login(self, host: str, port: int, username: str, password: str) -> int:
        return self.login_with_device_info(host, port, username, password).user_id

    def login_with_device_info(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
    ) -> HcNetSdkDeviceSession:
        login_info = NET_DVR_USER_LOGIN_INFO()
        login_info.sDeviceAddress = host.encode()
        login_info.wPort = port
        login_info.sUserName = username.encode()
        login_info.sPassword = password.encode()
        device_info = NET_DVR_DEVICEINFO_V40()
        user_id = int(self.sdk.NET_DVR_Login_V40(byref(login_info), byref(device_info)))
        if user_id < 0:
            raise HcNetSdkError(f"NET_DVR_Login_V40 failed: {self.last_error()}")
        return HcNetSdkDeviceSession(user_id=user_id, channels=tuple(channels_from_device_info(device_info)))


@dataclass
class PlaybackSession:
    sdk: HcNetSdkLibrary
    stream_name: str
    host: str
    port: int
    username: str
    password: str
    channel: int
    start_time: datetime
    end_time: datetime
    rtmp_url: str
    playback_url: str
    timeout: float
    expires_at: float

    def __post_init__(self) -> None:
        self.user_id = -1
        self.playback_handle = -1
        self.ffmpeg: subprocess.Popen[bytes] | None = None
        self.callback: Any = None
        self.queue: queue.Queue[bytes | None] = queue.Queue(maxsize=256)
        self.writer: threading.Thread | None = None
        self.failed = ""

    def start(self) -> None:
        self.ffmpeg = subprocess.Popen(
            [
                "ffmpeg",
                "-nostdin",
                "-loglevel",
                "error",
                "-fflags",
                "nobuffer",
                "-re",
                "-i",
                "pipe:0",
                "-an",
                "-c:v",
                "copy",
                "-f",
                "flv",
                self.rtmp_url,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        self.writer = threading.Thread(target=self._write_ffmpeg_stdin, name="hcnetsdk-ffmpeg-writer", daemon=True)
        self.writer.start()

        self.sdk.sdk.NET_DVR_SetConnectTime(int(self.timeout * 1000), 1)
        self.sdk.sdk.NET_DVR_SetReconnect(10000, True)
        self.user_id = self.sdk.login(self.host, self.port, self.username, self.password)
        vod = self._vod_para()
        self.playback_handle = int(self.sdk.sdk.NET_DVR_PlayBackByTime_V40(self.user_id, byref(vod)))
        if self.playback_handle < 0:
            raise HcNetSdkError(f"NET_DVR_PlayBackByTime_V40 failed: {self.sdk.last_error()}")
        self.callback = PLAYBACK_CALLBACK(self._on_playback_data)
        if not self.sdk.sdk.NET_DVR_SetPlayDataCallBack_V40(self.playback_handle, self.callback, None):
            raise HcNetSdkError(f"NET_DVR_SetPlayDataCallBack_V40 failed: {self.sdk.last_error()}")
        output_size = c_uint32(0)
        if not self.sdk.sdk.NET_DVR_PlayBackControl_V40(
            self.playback_handle,
            NET_DVR_PLAYSTART,
            None,
            0,
            None,
            byref(output_size),
        ):
            raise HcNetSdkError(f"NET_DVR_PlayBackControl_V40 failed: {self.sdk.last_error()}")

    def stop(self) -> None:
        if self.playback_handle >= 0:
            self.sdk.sdk.NET_DVR_StopPlayBack(self.playback_handle)
            self.playback_handle = -1
        self.queue_put(None)
        if self.writer is not None:
            self.writer.join(timeout=5)
        if self.ffmpeg is not None:
            if self.ffmpeg.stdin is not None and not self.ffmpeg.stdin.closed:
                with suppress_io_errors():
                    self.ffmpeg.stdin.close()
            try:
                self.ffmpeg.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.ffmpeg.kill()
                self.ffmpeg.wait(timeout=5)
        if self.user_id >= 0:
            self.sdk.sdk.NET_DVR_Logout(self.user_id)
            self.user_id = -1

    def _vod_para(self) -> NET_DVR_VOD_PARA:
        vod = NET_DVR_VOD_PARA()
        vod.dwSize = sizeof(vod)
        vod.struIDInfo.dwSize = sizeof(vod.struIDInfo)
        vod.struIDInfo.dwChannel = self.channel
        vod.struBeginTime = to_sdk_time(self.start_time)
        vod.struEndTime = to_sdk_time(self.end_time)
        vod.hWnd = None
        vod.byDrawFrame = 0
        return vod

    def _on_playback_data(self, handle: int, data_type: int, buffer: Any, size: int, user: Any) -> None:
        if size <= 0 or not buffer:
            return
        self.queue_put(string_at(buffer, int(size)))

    def queue_put(self, item: bytes | None) -> None:
        try:
            self.queue.put(item, timeout=1)
        except queue.Full:
            self.failed = "HCNetSDK callback queue is full"

    def _write_ffmpeg_stdin(self) -> None:
        assert self.ffmpeg is not None
        stdin = self.ffmpeg.stdin
        if stdin is None:
            self.failed = "ffmpeg stdin is not available"
            return
        while True:
            item = self.queue.get()
            if item is None:
                break
            try:
                stdin.write(item)
                stdin.flush()
            except BrokenPipeError:
                self.failed = self.ffmpeg_error()
                break
            except Exception as exc:
                self.failed = str(exc)
                break
        with suppress_io_errors():
            stdin.close()

    def ffmpeg_error(self) -> str:
        if self.ffmpeg is None or self.ffmpeg.stderr is None:
            return "ffmpeg failed"
        try:
            error = self.ffmpeg.stderr.read().decode(errors="ignore").strip()
        except Exception:
            error = ""
        return error or f"ffmpeg exited with code {self.ffmpeg.poll()}"


class suppress_io_errors:
    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        return exc_type in {BrokenPipeError, OSError, ValueError}
