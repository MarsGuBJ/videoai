"""fetch_llm_models 解析逻辑单元测试：requests 在模块命名空间 mock。"""

import app.services.llm_configs as svc


class _FakeResponse:
    def __init__(self, status_code: int = 200, payload: object = None, json_error: bool = False):
        self.status_code = status_code
        self._payload = payload
        self._json_error = json_error

    def json(self) -> object:
        if self._json_error:
            raise ValueError("bad json")
        return self._payload


def test_fetch_llm_models_parses_data_ids_sorted(monkeypatch):
    payload = {"data": [{"id": "b-model"}, {"id": "a-model"}, {"id": " "}, "junk", {}]}
    monkeypatch.setattr(svc.requests, "get", lambda url, headers, timeout: _FakeResponse(payload=payload))

    result = svc.fetch_llm_models("https://example.com/v1/", "sk-x")

    assert result == {"ok": True, "models": ["a-model", "b-model"], "error": None}


def test_fetch_llm_models_non_2xx_returns_error(monkeypatch):
    monkeypatch.setattr(svc.requests, "get", lambda url, headers, timeout: _FakeResponse(status_code=401, payload={}))

    result = svc.fetch_llm_models("https://example.com/v1", "sk-x")

    assert result["ok"] is False
    assert result["models"] == []
    assert result["error"] == "HTTP 401"


def test_fetch_llm_models_missing_data_list_returns_error(monkeypatch):
    monkeypatch.setattr(svc.requests, "get", lambda url, headers, timeout: _FakeResponse(payload={"foo": 1}))

    result = svc.fetch_llm_models("https://example.com/v1", "sk-x")

    assert result["ok"] is False
    assert result["error"] == "响应缺少 data 模型列表"


def test_fetch_llm_models_empty_data_returns_error(monkeypatch):
    monkeypatch.setattr(svc.requests, "get", lambda url, headers, timeout: _FakeResponse(payload={"data": []}))

    result = svc.fetch_llm_models("https://example.com/v1", "sk-x")

    assert result["ok"] is False
    assert result["error"] == "服务未返回任何可用模型"


def test_fetch_llm_models_invalid_json_returns_error(monkeypatch):
    monkeypatch.setattr(svc.requests, "get", lambda url, headers, timeout: _FakeResponse(json_error=True))

    result = svc.fetch_llm_models("https://example.com/v1", "sk-x")

    assert result["ok"] is False
    assert result["error"] == "响应不是合法 JSON"


def test_fetch_llm_models_request_exception_returns_error(monkeypatch):
    def raise_exc(url, headers, timeout):
        raise svc.requests.ConnectionError("refused")

    monkeypatch.setattr(svc.requests, "get", raise_exc)

    result = svc.fetch_llm_models("https://example.com/v1", "sk-x")

    assert result["ok"] is False
    assert "ConnectionError" in result["error"]
