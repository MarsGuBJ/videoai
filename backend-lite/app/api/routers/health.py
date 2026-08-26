"""健康检查路由。"""

from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """返回服务存活状态。"""
    return HealthResponse(status="ok")
