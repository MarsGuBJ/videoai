"""以图搜人 / 文本检索 DTO。"""

from pydantic import BaseModel


class PersonSearchImageResponse(BaseModel):
    imageUrl: str
    imagePath: str


class PersonSearchDetectRequest(BaseModel):
    imageUrl: str


class PersonSearchByBboxRequest(BaseModel):
    imageUrl: str
    bbox: list[dict] | None = None
    searchMethod: str = "reid"
    startTime: str | None = None
    endTime: str | None = None
    similarityThreshold: float = 0.6
    topK: int = 10
    # 服务端属性筛选（上游 2026-10 新增，见 docs/person-api.md）：不传/传空 = 不过滤；
    # 启用后 ES 中该属性为空的记录会被过滤掉；多属性为 AND 关系
    sex: str | None = None
    age: str | None = None
    topColor: str | None = None


class PersonSearchReviewRequest(BaseModel):
    """大模型二次研判（searchPersonReview）：基准切片 + 勾选的命中记录 es_doc_id。"""

    imageUrl: str
    bbox: list[dict]
    esIds: list[str]


class TextSearchQueryRequest(BaseModel):
    message: str
    startTime: str | None = None
    endTime: str | None = None
    location: str | None = None
    page: int = 1
    pageSize: int = 10
    # 检索模式（Retrieve API 2026-10 新增）：exact 精确 / fuzzy 模糊语义 / balanced 均衡；不传由上游默认 exact
    searchMode: str | None = None
    # 模糊/均衡模式相似度阈值 0~1；不传由上游默认 0.5
    confidence: float | None = None
    # 时间排序 asc/desc，主要作用于精确检索；不传由上游默认 desc
    sortOrder: str | None = None
