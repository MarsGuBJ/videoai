"""VideoAI worker FastAPI app: face embedding, object detection and stream management routes."""

import asyncio
import threading
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import lru_cache
from uuid import UUID

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from . import monitor
from .config import settings
from .schemas import EmbeddingResponse, StreamStartRequest, StreamStatusResponse, StreamStopRequest
from .stream_manager import StreamManager
from .triton_models import DinoDetectionClient, TritonFaceClient

HEARTBEAT_THREAD_JOIN_TIMEOUT_SECONDS = 2


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """启动时拉起 GPU 监控心跳守护线程，关闭时置位停止事件并等待退出。"""
    stop_event = threading.Event()
    heartbeat_thread = threading.Thread(target=monitor.heartbeat_loop, args=(stop_event,), daemon=True)
    heartbeat_thread.start()
    yield
    stop_event.set()
    heartbeat_thread.join(timeout=HEARTBEAT_THREAD_JOIN_TIMEOUT_SECONDS)


app = FastAPI(title="VideoAI Worker", version="0.1.0", lifespan=lifespan)


@lru_cache
def face_client() -> TritonFaceClient:
    """Return the process-wide Triton face client (lazy singleton)."""
    return TritonFaceClient(settings())


@lru_cache
def dino_client() -> DinoDetectionClient | None:
    """Return the process-wide DINO detection client, or None when detection is disabled."""
    return DinoDetectionClient(settings()) if settings().object_detection_enabled else None


@lru_cache
def stream_manager() -> StreamManager:
    """Return the process-wide stream manager (lazy singleton)."""
    return StreamManager(settings(), face_client(), dino_client())


@app.get("/health")
def health():
    """Liveness probe."""
    return {"status": "ok"}


@app.post("/v1/faces/extract", response_model=EmbeddingResponse)
async def extract_face(file: UploadFile = File(...)):
    """Decode an uploaded image and return the embedding of its single face."""
    data = await file.read()
    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="invalid image")
    embedding = face_client().extract_embedding(image)
    return EmbeddingResponse(embedding=embedding)


@app.post("/v1/streams/start")
def start_stream(request: StreamStartRequest):
    """Start (or replace) the processing loop for one camera stream."""
    stream_manager().start(request)
    return {"status": "started"}


@app.post("/v1/streams/stop")
def stop_stream(request: StreamStopRequest):
    """Stop the processing loop for one camera stream."""
    stream_manager().stop(request.cameraId)
    return {"status": "stopped"}


@app.get("/v1/streams", response_model=StreamStatusResponse)
def streams():
    """Return the status of all managed streams."""
    return StreamStatusResponse(streams=stream_manager().status())


@app.get("/v1/streams/annotated.mjpeg")
async def annotated_mjpeg(cameraId: UUID = Query(...)):
    """Stream the latest annotated frames for one camera as multipart MJPEG."""

    async def generate():
        while True:
            frame = stream_manager().get_annotated_frame(str(cameraId))
            if frame is not None:
                ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if ok:
                    yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + encoded.tobytes() + b"\r\n")
            await asyncio.sleep(0.5)

    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")
