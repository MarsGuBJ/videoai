import base64
import logging
import subprocess
import threading
import time
from dataclasses import dataclass
from uuid import UUID

import cv2
import numpy as np
import requests

from .config import Settings
from .engines import loader
from .schemas import (
    AlgorithmSpec,
    FaceEventIngestRequest,
    FaceTarget,
    MatchRequest,
    MatchResponse,
    ObjectEventIngestRequest,
    StreamStartRequest,
    utc_now,
)
from .triton_models import DinoDetectionClient, TritonFaceClient, draw_object_boxes

# OpenCV 日志压到 ERROR：默认级别会把每次读帧/打开失败都以 WARN/ERROR 刷进容器日志
# （2026-09-28 实测 worker 日志 51.4 万行里 27.2 万行是这类噪声）。
# 说明：FFmpeg 自身（libavcodec，如 "[h264 @ ...] no frame!"）的消息不走 OpenCV 日志，
# 且其符号静态链接进 cv2 扩展、Python 侧无法关闭；那部分靠 _run 的重开自愈避免刷屏。
cv2.setLogLevel(2)  # 2 = ERROR（该 OpenCV 构建未导出 cv2.LOG_LEVEL_* 常量）

logger = logging.getLogger(__name__)

# 解码失败后重开 OpenCV 视频源的最小间隔（秒）：兜底 ffmpeg 在镜像内不可用时靠它自愈
CAPTURE_RETRY_INTERVAL_SECONDS = 10.0
# OpenCV 能打开但持续读不出帧时（典型是摄像头 H.265 而本机 OpenCV 无 HEVC 解封装），
# 允许重开 OpenCV 的最大次数；超过即弃用 OpenCV，强制走 ffmpeg 管道兜底
OPENCV_MAX_RECOVERY_ATTEMPTS = 2
# ffmpeg 兜底管道起播后最长无帧等待（秒）：超时判定管道卡死，杀掉重建
FFMPEG_PIPE_STALL_SECONDS = 30.0
# 同一路流处理失败日志的最小间隔（秒）：DINO/人脸/算法是按帧或按秒调用的，
# 上游持续故障（例如 Triton 缺模型）时会每帧吐一条 traceback（实测 2096 次/10 分钟）
FAILURE_LOG_COOLDOWN_SECONDS = 60.0


@dataclass
class StreamTask:
    """One running stream: its request, stop signal, worker thread and status."""

    request: StreamStartRequest
    stop_event: threading.Event
    thread: threading.Thread
    status: str = "starting"


class StreamManager:
    """Manage per-camera stream processing loops (start/stop/status/annotated frames)."""

    def __init__(self, settings: Settings, face_client: TritonFaceClient, dino_client: DinoDetectionClient = None):
        self.settings = settings
        self.face_client = face_client
        self.dino_client = dino_client
        self.tasks: dict[str, StreamTask] = {}
        self.lock = threading.Lock()
        self.detection_cooldowns: dict[str, float] = {}
        self.latest_annotated_frames: dict[str, np.ndarray] = {}
        # 失败日志限流：key -> 上次打印时间 / 被抑制的条数
        self._failure_log_at: dict[str, float] = {}
        self._failure_log_suppressed: dict[str, int] = {}

    def start(self, request: StreamStartRequest) -> None:
        """Start the processing loop for a stream, replacing any existing one."""
        key = str(request.cameraId)
        old_task = None
        with self.lock:
            old_task = self.tasks.pop(key, None)

        if old_task is not None:
            old_task.stop_event.set()
            old_task.thread.join(timeout=2)
            loader.release_engine(key)

        with self.lock:
            stop_event = threading.Event()
            self.latest_annotated_frames.pop(key, None)
            self._clear_detection_cooldowns_locked(key)
            task = StreamTask(
                request=request,
                stop_event=stop_event,
                thread=threading.Thread(target=self._run, args=(key, request, stop_event), daemon=True),
            )
            self.tasks[key] = task
            task.thread.start()

    def stop(self, camera_id: UUID) -> None:
        """Stop the processing loop for one camera, if running."""
        key = str(camera_id)
        with self.lock:
            task = self.tasks.pop(key, None)
            self.latest_annotated_frames.pop(key, None)
            self._clear_detection_cooldowns_locked(key)
        if task is not None:
            task.stop_event.set()
            task.thread.join(timeout=2)
            loader.release_engine(key)

    def status(self) -> dict[str, str]:
        """Return a snapshot of ``{camera_key: status}`` for all managed streams."""
        with self.lock:
            return {key: task.status for key, task in self.tasks.items()}

    def _log_throttled(self, key: str, message: str, exc: Exception | None = None) -> None:
        """按 FAILURE_LOG_COOLDOWN_SECONDS 限流同一条流的失败日志。

        处理失败是按帧/按秒发生的，上游持续故障时逐条 traceback 会把日志刷爆
        （实测 Triton 缺 dino_coco 模型时 2096 条/10 分钟）。这里每个 key 每 60s
        只打一条，并附上期间被抑制的条数。
        """
        now = time.monotonic()
        with self.lock:
            if now - self._failure_log_at.get(key, 0.0) < FAILURE_LOG_COOLDOWN_SECONDS:
                self._failure_log_suppressed[key] = self._failure_log_suppressed.get(key, 0) + 1
                return
            suppressed = self._failure_log_suppressed.pop(key, 0)
            self._failure_log_at[key] = now
        suffix = f"（期间另有 {suppressed} 次同类失败未打印）" if suppressed else ""
        if exc is None:
            logger.warning("%s%s", message, suffix)
        else:
            logger.warning("%s: %s%s", message, exc, suffix)

    def _set_status(self, key: str, status: str) -> None:
        with self.lock:
            task = self.tasks.get(key)
            if task is not None and task.thread is threading.current_thread():
                task.status = status

    def _clear_detection_cooldowns_locked(self, camera_key: str) -> None:
        prefix = f"{camera_key}:"
        stale = [key for key in self.detection_cooldowns if key.startswith(prefix)]
        for key in stale:
            self.detection_cooldowns.pop(key, None)

    def _run(self, key: str, request: StreamStartRequest, stop_event: threading.Event) -> None:
        capture = self._open_capture(request.streamUrl)
        if capture is not None:
            self._set_status(key, "running")
        frame_interval = 0.0 if self.settings.frame_sample_fps <= 0 else 1.0 / self.settings.frame_sample_fps
        last_frame_at = 0.0
        ffmpeg_proc = None
        failed_reads = 0
        retry_capture_at = 0.0
        # 第二种失败形态：OpenCV 能打开但持续读不出帧（典型是摄像头 H.265 而本机
        # OpenCV 的 ffmpeg 无 HEVC 解封装——isOpened() 正常、read() 永远失败，2026-09-29
        # 实测"1205有声摄像头" 30 次读取 0 帧）。旧逻辑只周期性重开 OpenCV，永远走不到
        # ffmpeg 兜底，该路流永久停在 reconnecting，布控任务抽不到帧也不产生事件。
        opencv_recovery_attempts = 0
        opencv_broken = False
        last_pipe_frame_at = time.monotonic()
        try:
            while not stop_event.is_set():
                frame = None
                if capture is not None:
                    ok, frame = capture.read()
                    if ok:
                        failed_reads = 0
                    else:
                        failed_reads += 1
                        frame = None
                    if frame is None and failed_reads >= 2 and not opencv_broken:
                        # OpenCV 读流持续失败：释放句柄，进入下方恢复流程
                        capture.release()
                        capture = None

                if frame is None and capture is None and ffmpeg_proc is None:
                    # 恢复流程：先限次重开 OpenCV；用尽或打不开则弃用 OpenCV、强制走
                    # ffmpeg 管道兜底。必须周期性重试：否则一次解码失败会让该路流
                    # 永久停在 reconnecting，布控任务再也不产生事件。
                    now = time.monotonic()
                    if now >= retry_capture_at:
                        if opencv_broken or opencv_recovery_attempts >= OPENCV_MAX_RECOVERY_ATTEMPTS:
                            opencv_broken = True
                            ffmpeg_proc = self._start_ffmpeg_pipe(request.streamUrl)
                            if ffmpeg_proc is not None:
                                last_pipe_frame_at = now
                            else:
                                self._log_throttled(
                                    key, f"ffmpeg fallback unavailable for camera {key} (ffmpeg not on PATH?)"
                                )
                        else:
                            opencv_recovery_attempts += 1
                            capture = self._open_capture(request.streamUrl)
                            if capture is not None:
                                failed_reads = 0
                                self._set_status(key, "running")
                            else:
                                opencv_broken = True
                                ffmpeg_proc = self._start_ffmpeg_pipe(request.streamUrl)
                                if ffmpeg_proc is not None:
                                    last_pipe_frame_at = now
                        retry_capture_at = now + CAPTURE_RETRY_INTERVAL_SECONDS
                    if capture is None and ffmpeg_proc is None:
                        self._set_status(key, "reconnecting")

                if frame is None and ffmpeg_proc is not None:
                    frame = self._read_ffmpeg_frame(ffmpeg_proc, 1920, 1080)
                    if frame is not None:
                        self._set_status(key, "running")
                        last_pipe_frame_at = time.monotonic()
                    elif ffmpeg_proc.poll() is not None:
                        # 管道已退出（ffmpeg 崩溃或流结束）：杀掉残留，按冷却间隔重建
                        try:
                            ffmpeg_proc.kill()
                        except OSError:
                            pass
                        ffmpeg_proc = None
                        retry_capture_at = time.monotonic() + CAPTURE_RETRY_INTERVAL_SECONDS
                        self._set_status(key, "reconnecting")
                    elif time.monotonic() - last_pipe_frame_at > FFMPEG_PIPE_STALL_SECONDS:
                        # 管道活着但长期无帧（流静默卡死）：杀掉重建，同样受冷却间隔约束
                        try:
                            ffmpeg_proc.kill()
                        except OSError:
                            pass
                        ffmpeg_proc = None
                        retry_capture_at = time.monotonic() + CAPTURE_RETRY_INTERVAL_SECONDS
                        self._log_throttled(key, f"ffmpeg pipe stalled for camera {key}, restarting")
                        self._set_status(key, "reconnecting")

                if frame is None:
                    time.sleep(0.5)
                    continue

                now = time.monotonic()
                if frame_interval > 0 and now - last_frame_at < frame_interval:
                    continue
                if frame_interval > 0:
                    last_frame_at = now
                self._process_frame(request, frame)
        finally:
            if capture is not None:
                capture.release()
            if ffmpeg_proc is not None:
                ffmpeg_proc.kill()
            self._set_status(key, "stopped")

    def _open_capture(self, stream_url: str):
        """打开 OpenCV 视频源；打不开时释放并返回 None（调用方按间隔重试）。"""
        capture = cv2.VideoCapture(stream_url)
        if not capture.isOpened():
            capture.release()
            return None
        return capture

    def _start_ffmpeg_pipe(self, stream_url: str):
        try:
            # ffmpeg 可执行文件由部署环境 PATH 提供，URL 来自后端登记的流地址。
            # 输出统一 scale+pad 到 1920x1080：_read_ffmpeg_frame 按固定字节数解析，
            # 摄像头实际分辨率不同（如 720p）也能读出完整帧。
            return subprocess.Popen(  # noqa: S603
                [  # noqa: S607
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-fflags",
                    "nobuffer",
                    "-flags",
                    "low_delay",
                    "-i",
                    stream_url,
                    "-an",
                    "-vf",
                    "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
                    "-c:v",
                    "rawvideo",
                    "-pix_fmt",
                    "bgr24",
                    "-f",
                    "rawvideo",
                    "pipe:1",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            return None

    def _read_ffmpeg_frame(self, proc, width, height):
        try:
            frame_size = width * height * 3
            raw = proc.stdout.read(frame_size)
            if len(raw) < frame_size:
                return None
            return np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))
        except (OSError, ValueError):
            return None

    def _process_frame(self, request: StreamStartRequest, frame) -> None:
        snapshot_base64 = ""
        if request.faceDetectionEnabled:
            try:
                targets = self._due_face_targets(request, time.monotonic())
                if not targets:
                    if request.objectDetectionEnabled:
                        self._process_dino_frame(request, frame, snapshot_base64)
                    return
                detections = self.face_client.detect_faces(frame)
                for detection in detections:
                    aligned = self.face_client.align_detection(frame, detection)
                    embedding = self.face_client.embed(aligned).tolist()
                    for target in targets:
                        match = self._match(embedding, target.faceProfileId)
                        if not match.matched or match.id is None:
                            continue
                        if not snapshot_base64:
                            snapshot_base64 = encode_jpeg(frame)
                        event = FaceEventIngestRequest(
                            cameraId=request.cameraId,
                            faceProfileId=match.id,
                            cameraName=request.cameraName,
                            profileName=match.name or "",
                            profileDescription=match.description,
                            facePhotoPath=match.photoPath or "",
                            snapshotBase64=snapshot_base64,
                            videoTime=utc_now(),
                            similarity=match.similarity,
                            deploymentTaskId=target.deploymentTaskId,
                        )
                        self._ingest_event(event)
            except Exception as exc:
                self._log_throttled(
                    f"{request.cameraId}:face", f"face processing failed for camera {request.cameraId}", exc
                )
                self._set_status(str(request.cameraId), f"face processing error: {exc}")

        if request.objectDetectionEnabled:
            self._process_dino_frame(request, frame, snapshot_base64)

        if request.algorithm is not None:
            self._process_algorithm_frame(request, request.algorithm, frame)

    def _process_algorithm_frame(self, request: StreamStartRequest, spec: AlgorithmSpec, frame) -> None:
        """按识别间隔（秒）限频对抽样帧跑算法引擎，检出转 object-ingest 事件。

        加载/推理/上报任何异常只记日志和状态，绝不让流线程崩溃。
        """
        camera_key = str(request.cameraId)
        try:
            if not self._algorithm_due(spec, camera_key, time.monotonic()):
                return
            engine = loader.acquire_engine(camera_key, spec)
            raw = engine.inference(frame)
            objects = loader.raw_to_objects(spec.engineType, raw)
            self.latest_annotated_frames[camera_key] = frame.copy()
            if not objects:
                return
            self._ingest_algorithm_event(request, spec, engine, raw, objects, frame)
        except Exception as exc:
            self._log_throttled(
                f"{camera_key}:algo:{spec.engineType}",
                f"algorithm {spec.engineType} processing failed for camera {camera_key}",
                exc,
            )
            self._set_status(camera_key, f"algorithm processing error: {exc}")

    def _algorithm_due(self, spec: AlgorithmSpec, camera_key: str, now: float) -> bool:
        """与 _due_face_targets 同款的识别间隔（秒）限频，键复用 detection_cooldowns。"""
        interval = float(max(1, int(spec.recognitionPerMinute or 60)))
        target_key = f"{camera_key}:algo:{spec.algorithmId}"
        with self.lock:
            last_seen = self.detection_cooldowns.get(target_key, 0.0)
            if now - last_seen < interval:
                return False
            self.detection_cooldowns[target_key] = now
        return True

    def _ingest_algorithm_event(
        self,
        request: StreamStartRequest,
        spec: AlgorithmSpec,
        engine,
        raw,
        objects: list[dict],
        frame,
    ) -> None:
        # eventType 取自引擎 build_result（其写死的分辨率等字段忽略）；失败时回退注册表默认值
        event_type = loader.registry_entry(spec.engineType).event_type
        try:
            result = engine.build_result(raw)
            if isinstance(result, dict) and result.get("eventType"):
                event_type = str(result["eventType"])
        except Exception:
            logger.warning("build_result failed for engine %s", spec.engineType, exc_info=True)
        h, w = frame.shape[:2]
        event = ObjectEventIngestRequest(
            cameraId=request.cameraId,
            cameraName=request.cameraName,
            objects=objects,
            snapshotBase64=encode_jpeg(frame),
            videoTime=utc_now(),
            frameWidth=w,
            frameHeight=h,
            eventType=event_type,
            deploymentTaskId=spec.deploymentTaskId or request.deploymentTaskId,
        )
        try:
            response = requests.post(
                f"{self.settings.backend_internal_url}/api/events/object-ingest",
                json=event.model_dump(mode="json"),
                timeout=10,
            )
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001  # 上报失败不阻断拉流，但必须留日志（原先静默 pass 导致问题无法定位）
            logger.warning("algorithm event ingest failed for camera %s: %s", request.cameraId, exc)

    def _process_dino_frame(self, request: StreamStartRequest, frame, snapshot_base64: str = "") -> None:
        camera_key = str(request.cameraId)
        self.latest_annotated_frames[camera_key] = frame.copy()
        self._set_status(camera_key, "running")
        if self.dino_client is None or not self.settings.object_detection_enabled:
            return
        try:
            object_detections = self.dino_client.detect_objects(frame)
            annotated = frame.copy()
            if object_detections:
                annotated = draw_object_boxes(annotated, object_detections, self.settings.dino_conf_thres)
                if not snapshot_base64:
                    snapshot_base64 = encode_jpeg(frame)
                self._ingest_object_events(request, object_detections, frame, snapshot_base64)
            self.latest_annotated_frames[camera_key] = annotated
        except Exception as exc:
            self._log_throttled(f"{camera_key}:dino", f"dino processing failed for camera {camera_key}", exc)
            self._set_status(camera_key, f"dino processing error: {exc}")

    def _match(self, embedding, face_profile_id=None) -> MatchResponse:
        payload = MatchRequest(
            embedding=embedding,
            threshold=self.settings.face_match_threshold,
            faceProfileId=face_profile_id,
        ).model_dump(mode="json")
        response = requests.post(
            f"{self.settings.backend_internal_url}/api/internal/match",
            json=payload,
            timeout=5,
        )
        response.raise_for_status()
        return MatchResponse(**response.json())

    def _face_targets(self, request: StreamStartRequest) -> list[FaceTarget]:
        if request.faceTargets:
            return request.faceTargets
        if request.faceProfileId is not None:
            return [FaceTarget(faceProfileId=request.faceProfileId, deploymentTaskId=request.deploymentTaskId)]
        return []

    def _due_face_targets(self, request: StreamStartRequest, now: float) -> list[FaceTarget]:
        due = []
        camera_key = str(request.cameraId)
        with self.lock:
            for target in self._face_targets(request):
                interval = float(max(1, int(target.recognitionPerMinute or 60)))
                target_key = f"{camera_key}:{target.deploymentTaskId or 'legacy'}:{target.faceProfileId}"
                last_seen = self.detection_cooldowns.get(target_key, 0.0)
                if now - last_seen < interval:
                    continue
                self.detection_cooldowns[target_key] = now
                due.append(target)
        return due

    def _ingest_event(self, event: FaceEventIngestRequest) -> None:
        response = requests.post(
            f"{self.settings.backend_internal_url}/api/events/ingest",
            json=event.model_dump(mode="json"),
            timeout=10,
        )
        response.raise_for_status()

    def _ingest_object_events(
        self, request: StreamStartRequest, detections: list, frame, snapshot_base64: str = ""
    ) -> None:
        h, w = frame.shape[:2]
        objects_payload = []
        for det in detections:
            objects_payload.append(
                {
                    "labelId": det.label_id,
                    "labelName": det.label_name,
                    "score": det.score,
                    "x1": float(det.bbox[0]),
                    "y1": float(det.bbox[1]),
                    "x2": float(det.bbox[2]),
                    "y2": float(det.bbox[3]),
                }
            )
        if not objects_payload:
            return
        snapshot = snapshot_base64 or encode_jpeg(frame)
        event = ObjectEventIngestRequest(
            cameraId=request.cameraId,
            cameraName=request.cameraName,
            objects=objects_payload,
            snapshotBase64=snapshot,
            videoTime=utc_now(),
            frameWidth=w,
            frameHeight=h,
        )
        try:
            response = requests.post(
                f"{self.settings.backend_internal_url}/api/events/object-ingest",
                json=event.model_dump(mode="json"),
                timeout=10,
            )
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001  # 上报失败不阻断拉流，但必须留日志（原先静默 pass 导致问题无法定位）
            logger.warning("dino event ingest failed for camera %s: %s", request.cameraId, exc)

    def get_annotated_frame(self, camera_id: str) -> np.ndarray | None:
        """Return the latest annotated frame for a camera, or None."""
        return self.latest_annotated_frames.get(camera_id)


def encode_jpeg(frame) -> str:
    """Encode a frame as a base64 data-URL JPEG string (empty string on failure)."""
    ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(encoded.tobytes()).decode("ascii")
