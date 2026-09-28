"""人脸照片库（外部人脸照片模块代理）DTO。"""

from pydantic import BaseModel, Field


class FaceLibraryPageRequest(BaseModel):
    """分页查询人脸照片库请求。

    keyword 映射到外部接口的 ``query.val``（描述信息 val 模糊匹配），
    不传则不筛选，结果按创建时间倒序。
    """

    current: int = Field(default=1, ge=1)
    size: int = Field(default=12, ge=1, le=100)
    keyword: str | None = None


class FaceLibraryRecord(BaseModel):
    """人脸照片记录（对应外部 FaceLibLabelVO）。"""

    id: str
    name: str | None = None
    url: str | None = None
    createTime: str | None = None
    description: list[dict] | None = None


class FaceLibraryPageResponse(BaseModel):
    """人脸照片分页结果（对应外部 PageBean）。"""

    total: int = 0
    current: int = 1
    size: int = 12
    records: list[FaceLibraryRecord] = []
