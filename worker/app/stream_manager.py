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
from .schemas import (
    FaceEventIngestRequest,
    FaceTarget,
    MatchRequest,
    MatchResponse,
    ObjectEventIngestRequest,
    StreamStartRequest,
    utc_now,
)
from .triton_models import DinoDetectionClient, TritonFaceClient, draw_object_boxes

logger = logging.getLogger(__name__)


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

    def start(self, request: StreamStartRequest) -> None:
        """Start the processing loop for a stream, replacing any existing one."""
        key = str(request.cameraId)
        old_task = None
        with self.lock:
            old_task = self.tasks.pop(key, None)

        if old_task is not None:
            old_task.stop_event.set()
            old_task.thread.join(timeout=2)

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

    def status(self) -> dict[str, str]:
        """Return a snapshot of ``{camera_key: status}`` for all managed streams."""
        with self.lock:
            return {key: task.status for key, task in self.tasks.items()}

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
        capture = cv2.VideoCapture(request.streamUrl)
        if not capture.isOpened():
            capture.release()
            capture = None
        else:
            self._set_status(key, "running")
        frame_interval = 0.0 if self.settings.frame_sample_fps <= 0 else 1.0 / self.settings.frame_sample_fps
        last_frame_at = 0.0
        ffmpeg_proc = None
        failed_reads = 0
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
                else:
                    failed_reads = 1

                if frame is None and ffmpeg_proc is None and failed_reads >= 2:
                    self._set_status(key, "reconnecting")
                    if capture is not None:
                        capture.release()
                        capture = None
                    ffmpeg_proc = self._start_ffmpeg_pipe(request.streamUrl)

                if frame is None and ffmpeg_proc is not None:
                    frame = self._read_ffmpeg_frame(ffmpeg_proc, 1920, 1080)
                    if frame is not None:
                        self._set_status(key, "running")

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

    def _start_ffmpeg_pipe(self, stream_url: str):
        try:
            # ffmpeg 可执行文件由部署环境 PATH 提供，URL 来自后端登记的流地址
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
                logger.exception("face processing failed for camera %s", request.cameraId)
                self._set_status(str(request.cameraId), f"face processing error: {exc}")

        if request.objectDetectionEnabled:
            self._process_dino_frame(request, frame, snapshot_base64)

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
            logger.exception("dino processing failed for camera %s", camera_key)
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
                per_minute = max(1, int(target.recognitionPerMinute or 60))
                interval = 60.0 / per_minute
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
        except Exception:  # noqa: S110, BLE001  # 事件上报失败不阻断拉流，丢弃本帧事件
            pass

    def get_annotated_frame(self, camera_id: str) -> np.ndarray | None:
        """Return the latest annotated frame for a camera, or None."""
        return self.latest_annotated_frames.get(camera_id)


def encode_jpeg(frame) -> str:
    """Encode a frame as a base64 data-URL JPEG string (empty string on failure)."""
    ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(encoded.tobytes()).decode("ascii")
