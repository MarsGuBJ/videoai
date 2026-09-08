"""backend-lite 测试共享夹具。"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app import state
from app.main import create_app


@pytest.fixture()
def client() -> Iterator[TestClient]:
    """隔离进程内内存态的 TestClient。

    不使用上下文管理器，避免触发 lifespan（数据库、media backend、worker 等外部依赖）；
    仅清理/还原路由直接读写的内存容器。
    """
    saved_faces = dict(state.faces_store)
    saved_tasks = dict(state.deployment_tasks_store)
    saved_algorithms = dict(state.algorithms_store)
    saved_llm_configs = dict(state.llm_configs_store)
    saved_review_types = dict(state.review_types_store)
    saved_review_tasks = dict(state.review_tasks_store)
    saved_review_schedules = dict(state.review_schedules_store)
    saved_worker_nodes = dict(state.worker_nodes_store)
    saved_event_infos = dict(state.event_infos_store)
    saved_dedup_rules = dict(state.event_dedup_rules_store)
    saved_push_tasks = dict(state.event_push_tasks_store)
    saved_search_keywords = list(state.search_keywords_store)
    state.faces_store.clear()
    state.deployment_tasks_store.clear()
    state.algorithms_store.clear()
    state.llm_configs_store.clear()
    state.review_types_store.clear()
    state.review_tasks_store.clear()
    state.review_schedules_store.clear()
    state.worker_nodes_store.clear()
    state.event_infos_store.clear()
    state.event_dedup_rules_store.clear()
    state.event_push_tasks_store.clear()
    state.search_keywords_store.clear()
    try:
        yield TestClient(create_app())
    finally:
        state.faces_store.clear()
        state.faces_store.update(saved_faces)
        state.deployment_tasks_store.clear()
        state.deployment_tasks_store.update(saved_tasks)
        state.algorithms_store.clear()
        state.algorithms_store.update(saved_algorithms)
        state.llm_configs_store.clear()
        state.llm_configs_store.update(saved_llm_configs)
        state.review_types_store.clear()
        state.review_types_store.update(saved_review_types)
        state.review_tasks_store.clear()
        state.review_tasks_store.update(saved_review_tasks)
        state.review_schedules_store.clear()
        state.review_schedules_store.update(saved_review_schedules)
        state.worker_nodes_store.clear()
        state.worker_nodes_store.update(saved_worker_nodes)
        state.event_infos_store.clear()
        state.event_infos_store.update(saved_event_infos)
        state.event_dedup_rules_store.clear()
        state.event_dedup_rules_store.update(saved_dedup_rules)
        state.event_push_tasks_store.clear()
        state.event_push_tasks_store.update(saved_push_tasks)
        state.search_keywords_store.clear()
        state.search_keywords_store.extend(saved_search_keywords)
