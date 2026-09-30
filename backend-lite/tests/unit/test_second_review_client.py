"""judge_event（万物核二次复核接口）报文与响应解析测试：mock requests.post。"""

import pytest
import requests

from app.services import second_review_client

FAKE_IMAGE = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
FAKE_VIDEO = b"\x00\x00\x00\x18fake-mp4-bytes"
ENDPOINT = "http://second-review.local"


class FakeResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


def _post_capture(captured, payload, status_code: int = 200):
    def fake_post(url, files, data, timeout):
        captured["url"] = url
        captured["files"] = files
        captured["data"] = data
        captured["timeout"] = timeout
        return FakeResponse(payload, status_code)

    return fake_post


def test_judge_event_detected_true_returns_valid(monkeypatch):
    captured = {}
    payload = {
        "code": 0,
        "message": "success",
        "data": {
            "result": {"detected": True, "confidence": 0.98, "reason": "检测到人员跌倒", "evidence": []},
            "raw_text": "raw",
        },
    }
    monkeypatch.setattr(requests, "post", _post_capture(captured, payload))

    verdict, reason = second_review_client.judge_event(
        endpoint=ENDPOINT,
        event_type="人员跌倒",
        prompt="请判断画面中是否有人跌倒",
        image_bytes=FAKE_IMAGE,
        event_id="task-1",
    )

    assert verdict == "有效"
    assert reason == "检测到人员跌倒"
    # multipart 表单字段与 URL 拼接
    assert captured["url"] == f"{ENDPOINT}/api/v1/second-review/upload"
    assert captured["data"]["event_type"] == "人员跌倒"
    assert captured["data"]["prompt"] == "请判断画面中是否有人跌倒"
    assert captured["data"]["event_id"] == "task-1"
    assert captured["data"]["timeout"] == "300"
    assert captured["timeout"] == 310  # 客户端超时 = 服务端 timeout + 10
    assert captured["files"]["image"] == ("snapshot.jpg", FAKE_IMAGE)
    assert "video" not in captured["files"]  # 无视频字节时不上送 video 字段


def test_judge_event_detected_false_returns_invalid(monkeypatch):
    captured = {}
    payload = {
        "code": 0,
        "data": {"result": {"detected": False, "reason": "未见目标事件"}, "raw_text": "raw"},
    }
    monkeypatch.setattr(requests, "post", _post_capture(captured, payload))

    verdict, reason = second_review_client.judge_event(
        endpoint=ENDPOINT,
        event_type="人员跌倒",
        prompt="提示词",
        image_bytes=FAKE_IMAGE,
        video_bytes=FAKE_VIDEO,
    )

    assert verdict == "无效"
    assert reason == "未见目标事件"
    assert captured["files"]["video"] == ("review-video.mp4", FAKE_VIDEO)


def test_judge_event_result_null_falls_back_to_raw_text(monkeypatch):
    long_raw = "无法解析" * 200  # 超过 500 字，验证截断
    payload = {"code": 0, "data": {"result": None, "raw_text": long_raw}}
    monkeypatch.setattr(requests, "post", _post_capture({}, payload))

    verdict, reason = second_review_client.judge_event(
        endpoint=ENDPOINT, event_type="人员跌倒", prompt="提示词", image_bytes=FAKE_IMAGE
    )

    assert verdict == ""
    assert reason == long_raw[: second_review_client.MAX_REASON_CHARS]


def test_judge_event_empty_reason_falls_back_to_raw_text(monkeypatch):
    payload = {"code": 0, "data": {"result": {"detected": True, "reason": ""}, "raw_text": "原始输出"}}
    monkeypatch.setattr(requests, "post", _post_capture({}, payload))

    verdict, reason = second_review_client.judge_event(
        endpoint=ENDPOINT, event_type="人员跌倒", prompt="提示词", image_bytes=FAKE_IMAGE
    )

    assert verdict == "有效"
    assert reason == "原始输出"


def test_judge_event_http_error_carries_detail(monkeypatch):
    payload = {"detail": "event_type 不在白名单"}
    monkeypatch.setattr(requests, "post", _post_capture({}, payload, status_code=422))

    with pytest.raises(requests.HTTPError) as exc_info:
        second_review_client.judge_event(
            endpoint=ENDPOINT, event_type="人员跌倒", prompt="提示词", image_bytes=FAKE_IMAGE
        )

    assert "422" in str(exc_info.value)
    assert "event_type 不在白名单" in str(exc_info.value)


def test_judge_event_http_error_carries_list_detail(monkeypatch):
    payload = {"detail": [{"loc": ["body", "image"], "msg": "field required"}]}
    monkeypatch.setattr(requests, "post", _post_capture({}, payload, status_code=400))

    with pytest.raises(requests.HTTPError) as exc_info:
        second_review_client.judge_event(
            endpoint=ENDPOINT, event_type="人员跌倒", prompt="提示词", image_bytes=FAKE_IMAGE
        )

    assert "field required" in str(exc_info.value)


def test_judge_event_missing_data_raises_value_error(monkeypatch):
    monkeypatch.setattr(requests, "post", _post_capture({}, {"code": 0}))

    with pytest.raises(ValueError, match="no data"):
        second_review_client.judge_event(
            endpoint=ENDPOINT, event_type="人员跌倒", prompt="提示词", image_bytes=FAKE_IMAGE
        )


def test_judge_event_requires_image_bytes():
    with pytest.raises(ValueError, match="image_bytes"):
        second_review_client.judge_event(endpoint=ENDPOINT, event_type="人员跌倒", prompt="提示词")
