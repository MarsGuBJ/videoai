# e2e 测试（占位）

端到端测试目录，按手册 3.2.1 分层预留。

- 范围：跨服务真实链路（backend-lite ↔ worker ↔ 数据库 ↔ 媒体后端），需 docker compose 环境。
- 当前暂无 e2e 用例；新增时用例放本目录，并在 CI 中以独立 job 运行（不并入 unit/integration 门禁）。
