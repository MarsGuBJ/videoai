from urllib.parse import urljoin

import httpx

from .models import Camera


class VideoAiClient:
    def __init__(self, base_url: str, timeout: float = 15) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def list_cameras(self) -> list[Camera]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/api/cameras")
            response.raise_for_status()
            return [Camera.model_validate(item) for item in response.json()]

    async def get_camera(self, camera_id: str) -> Camera:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/api/cameras/{camera_id}")
            response.raise_for_status()
            return Camera.model_validate(response.json())

    async def start_camera(self, camera_id: str) -> Camera:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/api/cameras/{camera_id}/start")
            response.raise_for_status()
            return Camera.model_validate(response.json())

    async def upload_face(self, image_base64: str, camera_id: str, model_name: str, name: str | None = None) -> dict:
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

    def absolute_url(self, url: str, public_base: str | None = None) -> str:
        if url.startswith(("rtsp://", "rtmp://")):
            return url
        base = public_base if public_base else self.base_url
        if url.startswith(("http://", "https://")):
            path = url.split("/", 3)[-1] if "/" in url.split("://", 1)[-1] else ""
            return urljoin(f"{base}/", path.lstrip("/"))
        return urljoin(f"{base}/", url.lstrip("/"))
