"""人脸扫描：对运行中摄像头抓帧、检测人脸区域并与档案比对。"""

import logging
import subprocess
import sys
from datetime import datetime, timezone
from uuid import uuid4

from app import state
from app.core.config import get_settings
from app.schemas.camera import CameraResponse
from app.schemas.face import FaceProfileResponse, FaceScanSummary
from app.services import camera_cache
from app.services.events import FaceEventInput, create_face_event
from app.utils.assets import asset_path, jpeg_data_url
from app.utils.cv_scripts import DETECT_FACE_REGIONS_SCRIPT, IMAGE_SIMILARITY_SCRIPT

logger = logging.getLogger(__name__)

CV_SUBPROCESS_TIMEOUT_SECONDS = 8
FACE_SCAN_CAPTURE_EXTRA_TIMEOUT_SECONDS = 5


def face_scan_loop() -> None:
    """后台扫描循环：按配置间隔对所有运行中摄像头执行一次人脸扫描。"""
    settings = get_settings()
    if settings.face_scan_initial_delay_seconds > 0:
        state.scanner_stop_event.wait(settings.face_scan_initial_delay_seconds)
    while not state.scanner_stop_event.is_set():
        try:
            scan_running_cameras()
        except Exception as exc:  # noqa: BLE001  # 扫描线程必须永不退出，单轮失败记录后继续
            logger.error("face scan failed: %s", exc)
        state.scanner_stop_event.wait(max(settings.face_scan_interval_seconds, 1))


def scan_running_cameras() -> FaceScanSummary:
    """对全部运行中摄像头执行一轮抓帧-检测-比对。

    Returns:
        本轮扫描的统计摘要。
    """
    now = datetime.now(timezone.utc)
    running_cameras = [camera for camera in camera_cache.all() if camera.status == "RUNNING"]
    summary = FaceScanSummary(
        cameras=len(running_cameras),
        faces=len(state.faces_store),
        framesCaptured=0,
        faceDetections=0,
        matches=0,
        errors=[],
        scannedAt=now,
    )
    if not running_cameras or not state.faces_store:
        return summary

    for camera in running_cameras:
        try:
            if camera.streamName == "camera1" and "测试" in camera.name:
                continue
            frame = capture_camera_frame(camera)
            if not frame:
                summary.errors.append(f"{camera.name}: cannot capture frame")
                continue
            summary.framesCaptured += 1
            face_regions = detect_face_regions(frame)
            if not face_regions:
                continue
            summary.faceDetections += len(face_regions)
            for face_region in face_regions:
                face, similarity = match_face(face_region)
                if face is None:
                    continue
                event = create_face_event(
                    FaceEventInput(
                        camera_id=camera.id,
                        face_profile_id=face.id,
                        camera_name=camera.name,
                        profile_name=face.name,
                        profile_description=face.description,
                        face_photo_url=face.photoUrl,
                        snapshot_base64=jpeg_data_url(frame),
                        video_time=now,
                        similarity=similarity,
                    )
                )
                if event is not None:
                    summary.matches += 1
        except Exception as exc:  # noqa: BLE001  # 单路摄像头异常汇总进 errors，不中断整轮扫描
            summary.errors.append(f"{camera.name}: {exc}")
    return summary


def capture_camera_frame(camera: CameraResponse) -> bytes:
    """用 ffmpeg 从摄像头流抓一帧 JPEG。

    Args:
        camera: 摄像头对象。

    Returns:
        JPEG 字节；抓取失败返回空字节串。
    """
    settings = get_settings()
    source_url = camera.sourceUrl
    if source_url.startswith("/api/streams/"):
        source_url = f"http://localhost:8081{source_url}"
    elif camera.playbackUrl.endswith(".mjpeg"):
        source_url = f"rtmp://localhost/{camera.streamApp}/{camera.streamName}"

    process = subprocess.run(  # noqa: S603  # 参数列表固定，源地址来自受信任的摄像头配置
        [
            settings.ffmpeg_bin,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-rw_timeout",
            str(settings.face_scan_timeout_seconds * 1_000_000),
            "-i",
            source_url,
            "-frames:v",
            "1",
            "-q:v",
            "3",
            "-f",
            "image2pipe",
            "-vcodec",
            "mjpeg",
            "pipe:1",
        ],
        capture_output=True,
        timeout=settings.face_scan_timeout_seconds + FACE_SCAN_CAPTURE_EXTRA_TIMEOUT_SECONDS,
    )
    if process.returncode != 0:
        return b""
    return process.stdout


def detect_face_regions(frame: bytes) -> list[bytes]:
    """用内嵌 OpenCV 脚本检测人脸区域并裁剪。

    Args:
        frame: JPEG 帧字节。

    Returns:
        裁剪后的人脸区域 JPEG 列表；脚本不可用或失败时返回原帧。
    """
    if not frame:
        return []
    try:
        result = subprocess.run(  # noqa: S603  # 执行自身解释器运行固定内嵌脚本
            [sys.executable, "-c", DETECT_FACE_REGIONS_SCRIPT],
            input=frame,
            capture_output=True,
            timeout=CV_SUBPROCESS_TIMEOUT_SECONDS,
        )
        if result.returncode == 2:
            return [frame]
        if result.returncode != 0 or len(result.stdout) < 2:
            return []
        count = int.from_bytes(result.stdout[:2], "big")
        offset = 2
        regions: list[bytes] = []
        for _ in range(count):
            if offset + 4 > len(result.stdout):
                break
            size = int.from_bytes(result.stdout[offset : offset + 4], "big")
            offset += 4
            if size <= 0 or offset + size > len(result.stdout):
                break
            regions.append(result.stdout[offset : offset + size])
            offset += size
        return regions
    except (OSError, subprocess.SubprocessError):
        return [frame]


def match_face(face_region: bytes) -> tuple[FaceProfileResponse | None, float]:
    """把人脸区域与全部档案逐一比对，取最优。

    Args:
        face_region: 人脸区域 JPEG 字节。

    Returns:
        (命中档案, 相似度)；未命中或低于阈值时档案为 None。
    """
    best_face: FaceProfileResponse | None = None
    best_similarity = -1.0
    for face in state.faces_store.values():
        similarity = image_similarity(face_region, face.photoUrl)
        if similarity > best_similarity:
            best_similarity = similarity
            best_face = face
    if best_face is None:
        return None, 0.0
    if best_similarity < get_settings().face_match_threshold:
        return None, best_similarity
    return best_face, best_similarity


def image_similarity(frame: bytes, face_photo_url: str) -> float:
    """用内嵌 OpenCV 脚本计算帧与档案照片的直方图相似度。

    Args:
        frame: 待比对 JPEG 字节。
        face_photo_url: 档案照片 URL。

    Returns:
        0.0~1.0 相似度；脚本不可用返回 1.0，失败返回 0.0（与原逻辑一致）。
    """
    settings = get_settings()
    face_path = asset_path(face_photo_url, settings.face_storage_dir)
    if face_path is None or not face_path.is_file():
        return 0.0
    temp_path = settings.snapshot_storage_dir / f"scan-{uuid4()}.jpg"
    try:
        temp_path.write_bytes(frame)
        result = subprocess.run(  # noqa: S603  # 执行自身解释器运行固定内嵌脚本
            [sys.executable, "-c", IMAGE_SIMILARITY_SCRIPT, str(temp_path), str(face_path)],
            capture_output=True,
            text=True,
            timeout=CV_SUBPROCESS_TIMEOUT_SECONDS,
        )
        if result.returncode == 3:
            return 1.0
        if result.returncode != 0:
            return 0.0
        return float(result.stdout.strip() or "0")
    except (OSError, subprocess.SubprocessError, ValueError):
        return 0.0
    finally:
        if temp_path.is_file():
            temp_path.unlink()
