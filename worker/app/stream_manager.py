import base64
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Dict
from uuid import UUID

import cv2
import numpy as np
import requests

from .config import Settings
from .schemas import FaceEventIngestRequest, MatchRequest, MatchResponse, StreamStartRequest, utc_now
from .triton_models import TritonFaceClient, align_face


@dataclass
class StreamTask:
    request: StreamStartRequest
    stop_event: threading.Event
    thread: threading.Thread
    status: str = "starting"


class StreamManager:
    def __init__(self, settings: Settings, face_client: TritonFaceClient):
        self.settings = settings
        self.face_client = face_client
        self.tasks: Dict[str, StreamTask] = {}
        self.lock = threading.Lock()

    def start(self, request: StreamStartRequest) -> None:
        key = str(request.cameraId)
        old_task = None
        with self.lock:
            old_task = self.tasks.pop(key, None)

        if old_task is not None:
            old_task.stop_event.set()
            old_task.thread.join(timeout=2)

        with self.lock:
            stop_event = threading.Event()
            task = StreamTask(
                request=request,
                stop_event=stop_event,
                thread=threading.Thread(target=self._run, args=(key, request, stop_event), daemon=True),
            )
            self.tasks[key] = task
            task.thread.start()

    def stop(self, camera_id: UUID) -> None:
        key = str(camera_id)
        with self.lock:
            task = self.tasks.pop(key, None)
        if task is not None:
            task.stop_event.set()
            task.thread.join(timeout=2)

    def status(self) -> Dict[str, str]:
        with self.lock:
            return {key: task.status for key, task in self.tasks.items()}

    def _set_status(self, key: str, status: str) -> None:
        with self.lock:
            task = self.tasks.get(key)
            if task is not None:
                task.status = status

    def _run(self, key: str, request: StreamStartRequest, stop_event: threading.Event) -> None:
        capture = cv2.VideoCapture(request.streamUrl)
        if not capture.isOpened():
            capture.release()
            capture = None
        else:
            self._set_status(key, "running")
        frame_interval = 1.0 / max(self.settings.frame_sample_fps, 0.1)
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
                if now - last_frame_at < frame_interval:
                    continue
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
            proc = subprocess.Popen(
                [
                    "ffmpeg",
                    "-hide_banner", "-loglevel", "error",
                    "-fflags", "nobuffer",
                    "-flags", "low_delay",
                    "-i", stream_url,
                    "-an", "-c:v", "rawvideo", "-pix_fmt", "bgr24",
                    "-f", "rawvideo", "pipe:1",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            return proc
        except Exception:
            return None

    def _read_ffmpeg_frame(self, proc, width, height):
        try:
            frame_size = width * height * 3
            raw = proc.stdout.read(frame_size)
            if len(raw) < frame_size:
                return None
            return np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))
        except Exception:
            return None

    def _process_frame(self, request: StreamStartRequest, frame) -> None:
        try:
            detections = self.face_client.detect_faces(frame)
            for detection in detections:
                aligned = align_face(frame, detection.kps)
                embedding = self.face_client.embed(aligned).tolist()
                match = self._match(embedding)
                if not match.matched or match.id is None:
                    continue
                snapshot = encode_jpeg(frame)
                event = FaceEventIngestRequest(
                    cameraId=request.cameraId,
                    faceProfileId=match.id,
                    cameraName=request.cameraName,
                    profileName=match.name or "",
                    profileDescription=match.description,
                    facePhotoPath=match.photoPath or "",
                    snapshotBase64=snapshot,
                    videoTime=utc_now(),
                    similarity=match.similarity,
                )
                self._ingest_event(event)
        except Exception as exc:
            self._set_status(str(request.cameraId), f"processing error: {exc}")

    def _match(self, embedding) -> MatchResponse:
        response = requests.post(
            f"{self.settings.backend_internal_url}/api/internal/match",
            json=MatchRequest(embedding=embedding, threshold=self.settings.face_match_threshold).model_dump(),
            timeout=5,
        )
        response.raise_for_status()
        return MatchResponse(**response.json())

    def _ingest_event(self, event: FaceEventIngestRequest) -> None:
        response = requests.post(
            f"{self.settings.backend_internal_url}/api/events/ingest",
            json=event.model_dump(mode="json"),
            timeout=10,
        )
        response.raise_for_status()


def encode_jpeg(frame) -> str:
    ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(encoded.tobytes()).decode("ascii")
