"""对外开放接口路由（/api/open/*，供其他系统调用）。"""

from fastapi import APIRouter

from app.schemas.llm_config import LlmConfigOpenOut
from app.services.llm_configs import llm_config_open_out, require_llm_config

router = APIRouter()


@router.get("/api/open/llm-configs/{model_config_id}", response_model=LlmConfigOpenOut)
def get_llm_config_open(model_config_id: str) -> LlmConfigOpenOut:
    """按配置 ID 返回大模型配置信息（apiKey 明文，供其他系统直连大模型服务）。"""
    return llm_config_open_out(require_llm_config(model_config_id))
