"""事件配置（事件信息/去重规则/推送任务）路由契约测试：TestClient 直连，DB 落库在路由模块命名空间 mock。"""

from uuid import uuid4

from fastapi.testclient import TestClient

import app.api.routers.event_dedup_rules as dedup_rules_router
import app.api.routers.event_infos as event_infos_router
import app.api.routers.event_push_tasks as push_tasks_router

EVENT_INFO_PAYLOAD = {
    "name": "人员聚集",
    "code": "person_gather",
    "level": "高",
    "category": "安防",
    "mark": "多边形",
    "iconName": "gather.svg",
    "source": "算法",
    "eventSource": "视频分析",
    "algorithmCode": "algo-gather-v1",
    "attrs": [{"key": "threshold", "value": "5"}],
}

DEDUP_RULE_PAYLOAD = {
    "name": "聚集去重",
    "algorithm": "algo-gather-v1",
    "strategy": "时间维度去重",
    "durationMinutes": 10,
    "allCameras": False,
    "cameras": ["cam-01", "cam-02"],
    "remark": "十分钟内同人同事去重",
}

PUSH_TASK_PAYLOAD = {
    "name": "MQ 推送",
    "type": "mq",
    "address": "topic/event",
    "mqAddr": "tcp://mq:61616",
    "mqUser": "admin",
    "mqPass": "mq-secret-pass",
    "token": "plain-token-123",
    "expireDays": 30,
    "eventSource": "视频分析",
    "eventTypes": "person_gather",
    "desc": "推送到消息队列",
}


def _create_event_info(client: TestClient, monkeypatch, **overrides) -> dict:
    monkeypatch.setattr(event_infos_router, "persist_event_info", lambda record: None)
    response = client.post("/api/event-infos", json={**EVENT_INFO_PAYLOAD, **overrides})
    assert response.status_code == 200
    return response.json()


def _create_dedup_rule(client: TestClient, monkeypatch, **overrides) -> dict:
    monkeypatch.setattr(dedup_rules_router, "persist_dedup_rule", lambda record: None)
    response = client.post("/api/event-dedup-rules", json={**DEDUP_RULE_PAYLOAD, **overrides})
    assert response.status_code == 200
    return response.json()


def _create_push_task(client: TestClient, monkeypatch, **overrides) -> dict:
    monkeypatch.setattr(push_tasks_router, "persist_push_task", lambda record: None)
    response = client.post("/api/event-push-tasks", json={**PUSH_TASK_PAYLOAD, **overrides})
    assert response.status_code == 200
    return response.json()


# ---------------- 事件信息 /api/event-infos ----------------


def test_list_event_infos_empty_store_returns_empty_list(client: TestClient):
    response = client.get("/api/event-infos")

    assert response.status_code == 200
    assert response.json() == []


def test_create_event_info_missing_required_fields_returns_422(client: TestClient):
    response = client.post("/api/event-infos", json={})

    assert response.status_code == 422


def test_create_then_list_event_infos_returns_camel_case(client: TestClient, monkeypatch):
    created = _create_event_info(client, monkeypatch)

    assert created["name"] == "人员聚集"
    assert created["code"] == "person_gather"
    assert created["level"] == "高"
    assert created["mark"] == "多边形"
    assert created["iconName"] == "gather.svg"
    assert created["eventSource"] == "视频分析"
    assert created["algorithmCode"] == "algo-gather-v1"
    assert created["attrs"] == [{"key": "threshold", "value": "5"}]
    assert created["sortOrder"] == 1
    assert created["enabled"] is True
    assert created["id"]
    assert created["createdAt"]
    assert created["updatedAt"]

    second = _create_event_info(client, monkeypatch, name="区域入侵", code="intrusion")
    assert second["sortOrder"] == 2

    listed = client.get("/api/event-infos").json()
    assert len(listed) == 2
    # createdAt 倒序：后创建的排前面
    assert listed[0]["id"] == second["id"]
    assert listed[1]["id"] == created["id"]


def test_update_event_info_keeps_untouched_fields(client: TestClient, monkeypatch):
    created = _create_event_info(client, monkeypatch)

    response = client.put(
        f"/api/event-infos/{created['id']}",
        json={"name": "人员聚集（改）", "level": "中", "enabled": False, "sortOrder": 9},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "人员聚集（改）"
    assert payload["level"] == "中"
    assert payload["enabled"] is False
    assert payload["sortOrder"] == 9
    # 未传字段保留原值
    assert payload["code"] == "person_gather"
    assert payload["algorithmCode"] == "algo-gather-v1"


def test_update_event_info_unknown_id_returns_404(client: TestClient):
    response = client.put(f"/api/event-infos/{uuid4()}", json={"name": "x"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Event info not found"


def test_delete_event_info_removes_from_list(client: TestClient, monkeypatch):
    monkeypatch.setattr(event_infos_router, "delete_event_info_from_db", lambda event_id: None)
    created = _create_event_info(client, monkeypatch)

    response = client.delete(f"/api/event-infos/{created['id']}")

    assert response.status_code == 200
    assert response.json() == {"deleted": created["id"]}
    assert client.get("/api/event-infos").json() == []


def test_delete_event_info_unknown_id_returns_404(client: TestClient):
    response = client.delete(f"/api/event-infos/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Event info not found"


# ---------------- 去重规则 /api/event-dedup-rules ----------------


def test_list_dedup_rules_empty_store_returns_empty_list(client: TestClient):
    response = client.get("/api/event-dedup-rules")

    assert response.status_code == 200
    assert response.json() == []


def test_create_dedup_rule_missing_required_fields_returns_422(client: TestClient):
    response = client.post("/api/event-dedup-rules", json={})

    assert response.status_code == 422


def test_create_then_list_dedup_rules_returns_camel_case(client: TestClient, monkeypatch):
    created = _create_dedup_rule(client, monkeypatch)

    assert created["name"] == "聚集去重"
    assert created["algorithm"] == "algo-gather-v1"
    assert created["strategy"] == "时间维度去重"
    assert created["durationMinutes"] == 10
    assert created["similarity"] is None
    assert created["allCameras"] is False
    assert created["cameras"] == ["cam-01", "cam-02"]
    assert created["remark"] == "十分钟内同人同事去重"
    assert created["enabled"] is True
    assert created["id"]
    assert created["createdAt"]
    assert created["updatedAt"]

    listed = client.get("/api/event-dedup-rules").json()
    assert len(listed) == 1
    assert listed[0]["id"] == created["id"]
    assert listed[0]["allCameras"] is False


def test_create_dedup_rule_image_strategy_with_similarity(client: TestClient, monkeypatch):
    created = _create_dedup_rule(
        client,
        monkeypatch,
        strategy="实时重叠图像去重",
        durationMinutes=None,
        similarity=0.85,
    )

    assert created["strategy"] == "实时重叠图像去重"
    assert created["durationMinutes"] is None
    assert created["similarity"] == 0.85


def test_update_dedup_rule_keeps_untouched_fields(client: TestClient, monkeypatch):
    created = _create_dedup_rule(client, monkeypatch)

    response = client.put(
        f"/api/event-dedup-rules/{created['id']}",
        json={"name": "聚集去重（改）", "allCameras": True, "durationMinutes": 30},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "聚集去重（改）"
    assert payload["allCameras"] is True
    assert payload["durationMinutes"] == 30
    # 未传字段保留原值
    assert payload["strategy"] == "时间维度去重"
    assert payload["cameras"] == ["cam-01", "cam-02"]


def test_update_dedup_rule_unknown_id_returns_404(client: TestClient):
    response = client.put(f"/api/event-dedup-rules/{uuid4()}", json={"name": "x"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Dedup rule not found"


def test_delete_dedup_rule_removes_from_list(client: TestClient, monkeypatch):
    monkeypatch.setattr(dedup_rules_router, "delete_dedup_rule_from_db", lambda rule_id: None)
    created = _create_dedup_rule(client, monkeypatch)

    response = client.delete(f"/api/event-dedup-rules/{created['id']}")

    assert response.status_code == 200
    assert response.json() == {"deleted": created["id"]}
    assert client.get("/api/event-dedup-rules").json() == []


def test_delete_dedup_rule_unknown_id_returns_404(client: TestClient):
    response = client.delete(f"/api/event-dedup-rules/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Dedup rule not found"


# ---------------- 推送任务 /api/event-push-tasks ----------------


def test_list_push_tasks_empty_store_returns_empty_list(client: TestClient):
    response = client.get("/api/event-push-tasks")

    assert response.status_code == 200
    assert response.json() == []


def test_create_push_task_missing_required_fields_returns_422(client: TestClient):
    response = client.post("/api/event-push-tasks", json={})

    assert response.status_code == 422


def test_create_then_list_push_tasks_returns_masked_mq_pass_and_camel_case(client: TestClient, monkeypatch):
    created = _create_push_task(client, monkeypatch)

    assert created["name"] == "MQ 推送"
    assert created["type"] == "mq"
    assert created["mqAddr"] == "tcp://mq:61616"
    assert created["mqUser"] == "admin"
    assert created["mqPass"] == "mq-***"
    assert created["mqPassConfigured"] is True
    # token 明文返回
    assert created["token"] == PUSH_TASK_PAYLOAD["token"]
    assert created["expireDays"] == 30
    assert created["eventSource"] == "视频分析"
    assert created["eventTypes"] == "person_gather"
    # description 序列化为 desc
    assert created["desc"] == "推送到消息队列"
    assert "description" not in created
    assert created["enabled"] is True
    assert created["id"]
    assert created["createdAt"]
    assert created["updatedAt"]

    listed = client.get("/api/event-push-tasks").json()
    assert len(listed) == 1
    assert listed[0]["id"] == created["id"]
    assert listed[0]["mqPass"] == "mq-***"
    assert listed[0]["mqPassConfigured"] is True


def test_create_push_task_without_mq_pass_marks_unconfigured(client: TestClient, monkeypatch):
    created = _create_push_task(client, monkeypatch, mqPass="")

    assert created["mqPass"] == ""
    assert created["mqPassConfigured"] is False


def test_update_push_task_empty_mq_pass_keeps_original(client: TestClient, monkeypatch):
    created = _create_push_task(client, monkeypatch)

    response = client.put(
        f"/api/event-push-tasks/{created['id']}",
        json={"name": "HTTP 推送", "type": "http", "mqPass": "", "desc": "改为 HTTP"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "HTTP 推送"
    assert payload["type"] == "http"
    assert payload["desc"] == "改为 HTTP"
    # mqPass 传空保留原值：掩码与 configured 标记不变
    assert payload["mqPass"] == "mq-***"
    assert payload["mqPassConfigured"] is True


def test_update_push_task_new_mq_pass_replaces_original(client: TestClient, monkeypatch):
    created = _create_push_task(client, monkeypatch)

    response = client.put(f"/api/event-push-tasks/{created['id']}", json={"mqPass": "new-secret-456"})

    assert response.status_code == 200
    assert response.json()["mqPass"] == "new***"


def test_update_push_task_unknown_id_returns_404(client: TestClient):
    response = client.put(f"/api/event-push-tasks/{uuid4()}", json={"name": "x"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Push task not found"


def test_delete_push_task_removes_from_list(client: TestClient, monkeypatch):
    monkeypatch.setattr(push_tasks_router, "delete_push_task_from_db", lambda task_id: None)
    created = _create_push_task(client, monkeypatch)

    response = client.delete(f"/api/event-push-tasks/{created['id']}")

    assert response.status_code == 200
    assert response.json() == {"deleted": created["id"]}
    assert client.get("/api/event-push-tasks").json() == []


def test_delete_push_task_unknown_id_returns_404(client: TestClient):
    response = client.delete(f"/api/event-push-tasks/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Push task not found"
