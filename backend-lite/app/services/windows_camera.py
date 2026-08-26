"""Windows 摄像头（WSL 经 powershell.exe 推流）控制。"""

import shutil
import subprocess

from app import state
from app.core.config import get_settings
from app.schemas.windows_camera import WindowsCameraStatus

POWERSHELL_PROBE_TIMEOUT_SECONDS = 5
POWERSHELL_LIST_DEVICES_TIMEOUT_SECONDS = 8
HOSTNAME_TIMEOUT_SECONDS = 3
WINDOWS_CAMERA_STOP_WAIT_SECONDS = 4


def build_windows_camera_status() -> WindowsCameraStatus:
    """汇总当前 Windows 摄像头推流状态。

    Returns:
        包含可用性、运行状态、设备列表与发布地址的状态对象。
    """
    ffmpeg_path = find_windows_ffmpeg() if is_wsl_with_windows_tools() else None
    return WindowsCameraStatus(
        available=bool(ffmpeg_path),
        running=bool(state.windows_camera_process and state.windows_camera_process.poll() is None),
        ffmpegPath=ffmpeg_path,
        deviceName=state.windows_camera_device,
        streamName=state.windows_camera_stream,
        publishUrl=windows_rtmp_publish_url(state.windows_camera_stream),
        devices=list_windows_camera_devices(),
        message=None if ffmpeg_path else "Windows ffmpeg.exe not found. Run: winget install --id Gyan.FFmpeg -e",
    )


def is_wsl_with_windows_tools() -> bool:
    """判断当前环境是否可调用 powershell.exe（即 WSL 场景）。"""
    return shutil.which("powershell.exe") is not None


def find_windows_ffmpeg() -> str | None:
    """在 Windows 侧定位 ffmpeg.exe。

    Returns:
        ffmpeg.exe 的 Windows 路径；未找到或不在 WSL 时返回 None。
    """
    windows_ffmpeg_bin = get_settings().windows_ffmpeg_bin
    if not is_wsl_with_windows_tools():
        return None
    if "\\" in windows_ffmpeg_bin or ":" in windows_ffmpeg_bin:
        result = run_powershell(
            f"if (Test-Path {ps_quote(windows_ffmpeg_bin)}) {{ Write-Output {ps_quote(windows_ffmpeg_bin)} }}",
            timeout=POWERSHELL_PROBE_TIMEOUT_SECONDS,
        )
        output = result.stdout.strip()
        if result.returncode == 0 and output:
            return output.splitlines()[0]
    command = (
        f"$cmd = Get-Command {ps_quote(windows_ffmpeg_bin)} -ErrorAction SilentlyContinue; "
        "if ($cmd) { Write-Output $cmd.Source }"
    )
    result = run_powershell(command, timeout=POWERSHELL_PROBE_TIMEOUT_SECONDS)
    if result.returncode != 0:
        return None
    output = result.stdout.strip()
    return output.splitlines()[0] if output else None


def list_windows_camera_devices() -> list[str]:
    """枚举 Windows 侧摄像头设备名；不在 WSL 或查询失败时返回空列表。"""
    if not is_wsl_with_windows_tools():
        return []
    command = (
        "Get-CimInstance Win32_PnPEntity | "
        "Where-Object { $_.PNPClass -eq 'Camera' -or $_.Name -match 'Camera|摄像|Webcam|USB Video|Integrated' } | "
        "Select-Object -ExpandProperty Name"
    )
    result = run_powershell(command, timeout=POWERSHELL_LIST_DEVICES_TIMEOUT_SECONDS)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def windows_rtmp_publish_url(stream_name: str) -> str:
    """计算推流 RTMP 地址（WSL 本机 IP + live 应用）。

    Args:
        stream_name: 流名。

    Returns:
        rtmp:// 发布地址。
    """
    return f"rtmp://{local_wsl_ip()}/live/{stream_name}"


def local_wsl_ip() -> str:
    """取 WSL 本机首个 IP；失败回退 127.0.0.1。"""
    result = subprocess.run(  # noqa: S603  # 固定命令 hostname -I，无外部输入
        ["hostname", "-I"],  # noqa: S607  # 固定命令，依赖 PATH 解析为预期行为
        capture_output=True,
        text=True,
        timeout=HOSTNAME_TIMEOUT_SECONDS,
    )
    return result.stdout.split()[0] if result.stdout.split() else "127.0.0.1"


def windows_ffmpeg_command(ffmpeg_path: str, device_name: str, publish_url: str) -> str:
    """拼装 PowerShell 侧的 ffmpeg dshow 推流命令。

    Args:
        ffmpeg_path: ffmpeg.exe 路径。
        device_name: DirectShow 视频设备名。
        publish_url: RTMP 发布地址。

    Returns:
        PowerShell 命令字符串。
    """
    return (
        f"& {ps_quote(ffmpeg_path)} "
        "-hide_banner -loglevel warning -f dshow "
        f"-rtbufsize 256M -framerate 25 -video_size 1280x720 -i {ps_quote('video=' + device_name)} "
        "-an -c:v libx264 -preset veryfast -tune zerolatency -profile:v baseline "
        "-pix_fmt yuv420p -g 25 -keyint_min 25 -sc_threshold 0 "
        f"-f flv {ps_quote(publish_url)}"
    )


def ps_quote(value: str) -> str:
    """PowerShell 单引号转义。

    Args:
        value: 原始字符串。

    Returns:
        加引号并转义后的字符串。
    """
    return "'" + value.replace("'", "''") + "'"


def run_powershell(command: str, timeout: int) -> subprocess.CompletedProcess[str]:
    """经 powershell.exe 执行命令并捕获输出。

    Args:
        command: PowerShell 命令。
        timeout: 超时秒数。

    Returns:
        CompletedProcess（含 stdout/stderr/returncode）。
    """
    return subprocess.run(  # noqa: S603  # WSL 下固定调用 powershell.exe，命令由本模块构造
        ["powershell.exe", "-NoProfile", "-Command", command],  # noqa: S607  # WSL 约定经 PATH 调用 powershell.exe
        capture_output=True,
        text=True,
        timeout=timeout,
    )
