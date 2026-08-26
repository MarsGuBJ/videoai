"""内部接口路由（/api/internal/*，供 worker 等内部组件调用）。"""

from fastapi import APIRouter

from app import state
from app.core.config import get_settings
from app.schemas.face import FaceProfileResponse, MatchRequest, MatchResponse
from app.services.faces import cosine_similarity

router = APIRouter()


@router.post("/api/internal/match", response_model=MatchResponse)
def internal_match(request: MatchRequest) -> MatchResponse:
    """将上报向量与人脸库比对，返回最优命中结果。"""
    threshold = request.threshold if request.threshold is not None else get_settings().face_match_threshold
    best_face: FaceProfileResponse | None = None
    best_similarity = -1.0

    if request.faceProfileId is not None:
        target_id = request.faceProfileId
        target_face = state.faces_store.get(target_id)
        target_embedding = state.face_embeddings.get(target_id)
        if target_face is None or target_embedding is None:
            return MatchResponse(matched=False, similarity=0.0)
        similarity = cosine_similarity(request.embedding, target_embedding)
        if similarity < threshold:
            return MatchResponse(matched=False, similarity=max(0.0, similarity))
        return MatchResponse(
            matched=True,
            id=target_face.id,
            name=target_face.name,
            description=target_face.description,
            photoPath=target_face.photoUrl,
            similarity=max(0.0, min(1.0, similarity)),
        )

    for face_id, stored_embedding in state.face_embeddings.items():
        face = state.faces_store.get(face_id)
        if face is None:
            continue
        similarity = cosine_similarity(request.embedding, stored_embedding)
        if similarity > best_similarity:
            best_similarity = similarity
            best_face = face
    if best_face is None or best_similarity < threshold:
        return MatchResponse(matched=False, similarity=max(0.0, best_similarity))
    return MatchResponse(
        matched=True,
        id=best_face.id,
        name=best_face.name,
        description=best_face.description,
        photoPath=best_face.photoUrl,
        similarity=max(0.0, min(1.0, best_similarity)),
    )
