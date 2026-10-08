"""人脸照片库代理路由：转发外部人脸照片模块的分页查询。"""

from fastapi import APIRouter

from app.schemas.face_library import FaceLibraryPageRequest, FaceLibraryPageResponse
from app.services.face_library import query_face_page

router = APIRouter(tags=["人脸库"])


@router.post("/api/face-library/page", response_model=FaceLibraryPageResponse)
def face_library_page(request: FaceLibraryPageRequest) -> FaceLibraryPageResponse:
    """分页查询人脸照片库，供布控任务弹窗「从人脸库选取」使用。"""
    data = query_face_page(current=request.current, size=request.size, keyword=request.keyword)
    return FaceLibraryPageResponse(
        total=int(data.get("total") or 0),
        current=int(data.get("current") or request.current),
        size=int(data.get("size") or request.size),
        records=data.get("records") or [],
    )
