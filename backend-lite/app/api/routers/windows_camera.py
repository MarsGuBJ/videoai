"""Windows 摄像头推流控制路由。"""

import subprocess

from fastapi import APIRouter, HTTPException

from app import state
from app.schemas.windows_camera import WindowsCameraStartRequest, WindowsCameraStatus
from app.services.windows_camera import (
    build_windows_camera_status,
    find_windows_ffmpeg,
    is_wsl_with_windows_tools,
    windows_ffmpeg_command,
    windows_rtmp_publish_url,
)

router = APIRouter()


@router.get("/api/windows-camera/status", response_model=WindowsCameraStatus)
def windows_camera_status() -> WindowsCameraStatus:
    """返回 Windows 摄像头推流状态。"""
    return build_windows_camera_status()


@router.post("/api/windows-camera/start", response_model=WindowsCameraStatus)
def start_windows_camera(request: WindowsCameraStartRequest) -> WindowsCameraStatus:
    """启动 Windows 摄像头 ffmpeg 推流（仅 WSL + powershell.exe 环境）。"""
    if not is_wsl_with_windows_tools():
        raise HTTPException(
            status_code=400,
            detail="Windows camera control is only available from WSL with powershell.exe",
        )

    ffmpeg_path = find_windows_ffmpeg()
    if not ffmpeg_path:
        raise HTTPException(
            status_code=500,
            detail="Windows ffmpeg.exe not found. Install it with: winget install --id Gyan.FFmpeg -e",
        )

    if state.windows_camera_process and state.windows_camera_process.poll() is None:
        return build_windows_camera_status()

    state.windows_camera_device = request.deviceName or state.windows_camera_device
    state.windows_camera_stream = request.streamName or state.windows_camera_stream
    publish_url = windows_rtmp_publish_url(state.windows_camera_stream)
    state.windows_camera_process = subprocess.Popen(  # noqa: S603  # 固定调用 powershell.exe，命令由服务层构造
        [  # noqa: S607  # WSL 约定经 PATH 调用 powershell.exe
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            windows_ffmpeg_command(ffmpeg_path, state.windows_camera_device, publish_url),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )
    return build_windows_camera_status()


@router.post("/api/windows-camera/stop", response_model=WindowsCameraStatus)
def stop_windows_camera() -> WindowsCameraStatus:
    """停止 Windows 摄像头推流子进程。"""
    if state.windows_camera_process and state.windows_camera_process.poll() is None:
        state.windows_camera_process.terminate()
        try:
            state.windows_camera_process.wait(timeout=4)
        except subprocess.TimeoutExpired:
            state.windows_camera_process.kill()
    state.windows_camera_process = None
    return build_windows_camera_status()
