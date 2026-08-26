from typing import Any

import httpx


class PersonApiClient:
    def __init__(self, base_url: str, timeout: float = 15, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.transport = transport

    async def detect_persons(self, image_url: str) -> dict:
        return await self._post("/vlm-application/search/detectPersons", {"image_url": required(image_url, "imageUrl")})

    async def search_person_by_bbox(
        self,
        image_url: str,
        bbox: list[dict[str, Any]] | None = None,
        search_method: str = "reid",
        start_time: str = "",
        end_time: str = "",
        similarity_threshold: float = 0.6,
        top_k: int = 10,
    ) -> dict:
        payload: dict[str, Any] = {
            "image_url": required(image_url, "imageUrl"),
            "search_method": search_method or "reid",
            "similarity_threshold": similarity_threshold,
            "top_k": top_k,
        }
        if bbox is not None:
            payload["bbox"] = bbox
        if start_time:
            payload["start_time"] = start_time
        if end_time:
            payload["end_time"] = end_time
        return await self._post("/vlm-application/search/searchPersonByBbox", payload)

    async def get_person_search_result(self, task_id: str) -> dict:
        safe_task_id = required(task_id, "taskId")
        return await self._get(f"/vlm-application/search/searchPersonResult/{safe_task_id}")

    async def detect_persons_with_id(self, image_url: str) -> dict:
        return await self._post(
            "/vlm-application/search/detectPersonsWithId", {"image_url": required(image_url, "imageUrl")}
        )

    async def get_person_bbox(self, person_id: str) -> dict:
        safe_person_id = required(person_id, "personId")
        return await self._get(f"/vlm-application/search/getPersonBbox/{safe_person_id}")

    async def gait_feature_compare(self, persons: list[dict[str, Any]]) -> dict:
        if not isinstance(persons, list):
            raise ValueError("persons must be a JSON array")
        return await self._post("/vlm-application/gait/gaitFeaCompare", persons)

    async def _get(self, path: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            response = await client.get(f"{self.base_url}{path}")
        return parse_response(response)

    async def _post(self, path: str, payload: Any) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            response = await client.post(f"{self.base_url}{path}", json=payload)
        return parse_response(response)


def parse_response(response: httpx.Response) -> dict:
    try:
        payload = response.json()
    except ValueError:
        payload = {"message": response.text}
    if 200 <= response.status_code < 300:
        return payload
    if 400 <= response.status_code < 500:
        if isinstance(payload, dict):
            return {"upstreamStatusCode": response.status_code, **payload}
        return {"upstreamStatusCode": response.status_code, "data": payload}
    response.raise_for_status()
    return payload


def required(value: str, name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{name} is required")
    return normalized
