"""健康检查 DTO。"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
