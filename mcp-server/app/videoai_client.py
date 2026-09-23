import base64
import uuid
from urllib.parse import urljoin

import httpx

from .models import Camera


class CameraNotFoundError(ValueError):
    """cameraId 非法或摄像头不存在；按调用方参数错误处理（HTTP 400），不放大成上游 500。"""


def normalize_camera_id(camera_id: str | None) -> str:
    """校验并规范化 cameraId，返回小写标准 UUID 字符串。

    backend-media（Java）对非 UUID 的 cameraId 会返回类型转换 500，因此这里在发起请求前
    用 UUID 解析拦截调用方输入错误：非法输入抛 ``CameraNotFoundError``（``ValueError`` 子类，
    HTTP 层映射为 400）。首尾空白与 ``{uuid}`` 包裹形式会被规范化。
    """
    raw = str(camera_id).strip() if camera_id is not None else ""
    if raw.startswith("{") and raw.endswith("}"):
        raw = raw[1:-1].strip()
    try:
        return str(uuid.UUID(raw))
    except (ValueError, AttributeError, TypeError):
        raise CameraNotFoundError(f"{camera_id!r} is not a valid camera id") from None


class VideoAiClient:
    def __init__(self, base_url: str, timeout: float = 15, media_base_url: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.media_base_url = (media_base_url or base_url).rstrip("/")
        self.timeout = timeout

    async def list_cameras(self) -> list[Camera]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.media_base_url}/api/cameras")
            response.raise_for_status()
            return [Camera.model_validate(item) for item in response.json()]

    async def get_camera(self, camera_id: str) -> Camera:
        # 非法 cameraId 不发起上游请求（避免上游 UUID 类型转换 500）；上游 404 是客户端错误。
        normalized = normalize_camera_id(camera_id)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.media_base_url}/api/cameras/{normalized}")
            if response.status_code == 404:
                raise CameraNotFoundError(f"camera not found: {normalized}")
            response.raise_for_status()
            return Camera.model_validate(response.json())

    async def start_camera(self, camera_id: str) -> Camera:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.media_base_url}/api/cameras/{camera_id}/start")
            response.raise_for_status()
            return Camera.model_validate(response.json())

    async def upload_face(self, image_url: str, camera_id: str, model_name: str, name: str | None = None) -> dict:
        image_base64 = await self._download_image_as_base64(image_url)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload: dict = {"imageBase64": image_base64, "cameraId": camera_id, "modelName": model_name}
            if name:
                payload["name"] = name
            response = await client.post(
                f"{self.base_url}/api/faces/upload-base64",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def get_face(self, face_id: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/api/faces")
            response.raise_for_status()
            for face in response.json():
                if str(face.get("id")) == str(face_id):
                    return face
        raise ValueError(f"face profile not found after upload: {face_id}")

    async def create_deployment_task(self, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/api/deployment-tasks", json=payload)
            response.raise_for_status()
            return response.json()

    async def _download_image_as_base64(self, image_url: str) -> str:
        if not image_url or not image_url.strip():
            raise ValueError("imageUrl is required")
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(image_url.strip(), headers={"User-Agent": "VideoAI-MCP/1.0"})
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            if content_type and not content_type.startswith("image/"):
                raise ValueError("imageUrl must point to an image")
            data = response.content
            if not data:
                raise ValueError("imageUrl returned empty content")
            return base64.b64encode(data).decode("ascii")

    async def query_face_matches(self, face_id: str | None = None, limit: int = 10) -> list[dict]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            params = {"limit": str(max(1, min(limit, 10)))}
            if face_id:
                params["faceId"] = face_id
            response = await client.get(
                f"{self.base_url}/api/events/match",
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def list_deployment_tasks(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/api/deployment-tasks")
            response.raise_for_status()
            return response.json()

    def absolute_url(self, url: str, public_base: str | None = None) -> str:
        if url.startswith(("rtsp://", "rtmp://")):
            return url
        base = public_base if public_base else self.base_url
        if url.startswith(("http://", "https://")):
            path = url.split("/", 3)[-1] if "/" in url.split("://", 1)[-1] else ""
            return urljoin(f"{base}/", path.lstrip("/"))
        return urljoin(f"{base}/", url.lstrip("/"))
