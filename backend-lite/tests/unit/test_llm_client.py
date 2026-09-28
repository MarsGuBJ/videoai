"""judge_event 视频多帧分支的报文测试：mock requests.post 断言上送内容。"""

import requests

from app.services import llm_client

FAKE_FRAME_A = b"\xff\xd8\xff\xe0frame-a"
FAKE_FRAME_B = b"\xff\xd8\xff\xe0frame-b"
FAKE_FRAME_C = b"\xff\xd8\xff\xe0frame-c"


class FakeResponse:
    status_code = 200

    def json(self):
        return {"choices": [{"message": {"content": '{"verdict":"有效","reason":"检测到目标"}'}}]}

    def raise_for_status(self):
        return None


def _post_capture(captured):
    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return FakeResponse()

    return fake_post


def test_judge_event_single_image_keeps_original_instruction(monkeypatch):
    captured = {}
    monkeypatch.setattr(requests, "post", _post_capture(captured))

    verdict, _reason = llm_client.judge_event(
        base_url="http://llm.local/v1",
        api_key="",
        model="qwen-vl",
        prompt="判定提示词",
        image_bytes=FAKE_FRAME_A,
        timeout=30,
        temperature=0.0,
        max_tokens=1024,
    )

    assert verdict == "有效"
    content = captured["json"]["messages"][1]["content"]
    assert content[0]["text"] == llm_client.JUDGE_INSTRUCTION
    images = [part for part in content if part["type"] == "image_url"]
    assert len(images) == 1


def test_judge_event_with_extra_frames_sends_all_frames(monkeypatch):
    captured = {}
    monkeypatch.setattr(requests, "post", _post_capture(captured))

    verdict, _reason = llm_client.judge_event(
        base_url="http://llm.local/v1",
        api_key="",
        model="qwen-vl",
        prompt="判定提示词",
        image_bytes=FAKE_FRAME_A,
        extra_frames=[FAKE_FRAME_B, FAKE_FRAME_C],
        timeout=30,
        temperature=0.0,
        max_tokens=1024,
    )

    assert verdict == "有效"
    content = captured["json"]["messages"][1]["content"]
    assert content[0]["text"] == llm_client.JUDGE_VIDEO_INSTRUCTION
    images = [part for part in content if part["type"] == "image_url"]
    assert len(images) == 3
