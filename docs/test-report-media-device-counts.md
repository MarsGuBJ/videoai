# 设备管理页（/media）设备数量核验报告

- 被测地址：http://10.10.3.100:5173/media （视频管理页，设备列表 + 全部设备/在线/离线/从未连接成功/弱密码 统计页签）
- 服务器：10.10.3.100（public），项目目录 /home/public/videoai
- 核验时间：2026-09-16（UTC+8 约 20:30）
- 数据来源：页面真实渲染（Chrome headless + CDP）、`GET /api/cameras`（8083 直连与 5173 nginx 反代两条链路）、PostgreSQL `cameras` 表、ZLM `getMediaList`、backend-media 容器日志、对全部 363 台设备源地址的 TCP 探测

## 一、结论

| 页面指标 | 页面显示 | 数据库/接口 | 独立核验结果 | 判定 |
| --- | --- | --- | --- | --- |
| 全部设备 | **363** | 363 条记录（RUNNING 82 / STOPPED 281） | 记录数与库完全一致；但 363 条中含 3 条重复流地址记录，实际不同拉流地址 360 个 | 数值准确，数据有冗余 |
| 在线 | **82** | RUNNING 82 | 82 条中 **81 条**能实际拉到可播放 FLV；1 条（`0915测试`）无流但状态仍为 RUNNING | **高估 1 台**（假在线） |
| 离线 | **281** | STOPPED 281 | 281 台设备源地址 **TCP 554 全部可达**（在线）；均为 2026-07-29 批量导入后从未启动拉流的记录 | **数值与库一致，但语义不准确**（把"未启动"当"离线"） |

页面自身三数自洽：82 + 281 = 363，与各页签列表页脚（在线 82 条 / 离线 281 条 / 全部 363 条）一致，不存在前端算错。

## 二、页面实测证据

Chrome headless（`--headless=new` + CDP `Runtime.evaluate`）渲染 http://10.10.3.100:5173/media：

```
页签：['全部设备 363', '在线 82', '离线 281', '从未连接成功 0', '弱密码 1']
全部设备页脚：显示 1-10 共 363 条记录
点击"在线"：显示 1-10 共 82 条记录
点击"离线"：显示 1-10 共 281 条记录
```

首屏与前 10 行状态列均为"在线"（排序把 RUNNING 排在前面）。

## 三、逐项核验

### 1. 全部设备 = 363（与库一致）

```
数据库：SELECT count(*) FROM cameras;            -> 363
接口：  curl 8083/api/cameras                    -> 363（Counter RUNNING 82 / STOPPED 281）
接口：  curl 5173/api/cameras（nginx 反代）      -> 363（同样分布）
页面：  全部设备 363
```

库存中不存在第二处设备清单可被页面漏算：`cloud_platforms=1`（仅平台配置，`cameras.cloud_platform_id` 全为 NULL）、`access_config/gb28181/ga1400` 均为单行接入配置而非设备清单，因此 363 就是全量设备记录数。

数据冗余（会让"设备数"偏大）：

- `distinct source_url = 360`，即 3 条记录与其他记录共用同一拉流地址；
- 2026-09-15 新增的测试记录 3 条：
  - `NVR252通道32-设备--测试数据`、`NVR252通道32-设备--测试数据2` 与正式设备 `北面围墙枪机08` 使用完全相同的 `rtsp://admin:***@10.10.1.94:554/Streaming/Channels/101`（ZLM 中该 originUrl 被 3 路代理同时拉取，已实测确认）；
  - `0915-2` 与 `2#配电室枪机02` 共用 `rtsp://admin:***@10.10.1.13:554/Streaming/Channels/101`。
- 因此同一条物理视频流被同时计入"在线"（`0915-2`）和"离线"（`2#配电室枪机02`）；10.10.1.94 那一路被计入"在线"3 次。
- 另有 10 组重名设备、24 组重复 ip:port（多为同一设备的 101/201 主/子通道，属正常）。

### 2. 在线 = 82（高估 1 台）

- ZLM `getMediaList`：82 台 RUNNING 中 81 台的 `streamName` 存在于活动流列表；`0915测试`（id `eafc6762-…`）不存在。
- 逐个实测 `GET /api/live/{streamName}.live.flv`（8s 超时，检查 FLV 头）：
  - 81 台返回可播放 FLV；
  - `0915测试` 超时无数据；对照组（40 台非 RUNNING 设备）0 台可播，说明该方法有效。
- 该设备 `sourceUrl = rtsp://10.10.7.252:554/`（无凭据、无通道路径），backend-media 日志中每 30 秒重试并失败：

```
stream_proxy_guard: re-adding proxy for eafc6762-3fd2-49d7-8ead-59640a826cd4
ZLM addStreamProxy error for eafc6762-…: {code=-1, msg=OPTIONS:404 Not Found}
```

- 但它仍显示"在线"，原因链（代码在 `backend/monitoring-core`）：
  1. `CameraServiceImpl.start()` 先 `updateStatus(id,"RUNNING")` 再挂 ZLM 代理，代理失败不回滚状态；
  2. `StreamGuardServiceImpl.reconcileStreams()` 每 30s 发现缺流只会重挂代理，**从不把失败设备降级为 OFFLINE**；
  3. `CameraStatusScanService`（每 10 分钟）对 RUNNING/OFFLINE 设备做 TCP 探测，只有"端口不可达"才 RUNNING→OFFLINE。10.10.7.252 的 554 端口是通的，所以探测通过、状态永远保持 RUNNING → 页面长期显示"在线"。

### 3. 离线 = 281（数值对，语义错）

- 从服务器对 **全部 363 台**设备的 `sourceUrl` 做 TCP connect 探测（2.5s 超时，与后端扫描同一口径）：
  - 可达 **363 台**，不可达 0 台；
  - 对照组（10.10.0.254 / 10.10.1.250 / 10.10.2.250 / 10.10.3.250 / 10.10.9.9 等未使用地址）全部超时，证明"全通"不是网络中间设备造成的假信号。
- 也就是说，被判为"离线"的 281 台设备当前**网络可达、设备在线**，只是平台侧没有拉流：
  - 281 条的 `status=STOPPED`，且 `updated_at` 全部为 **2026-07-29**（批量导入当天），此后 7 周内没有任何变更 → 属于"导入后从未点过启动"的设备，而非掉线设备；
  - `STOPPED` 在代码中表示"用户手动停止/新建默认值"；`CameraStatusScanService` 明确跳过 STOPPED（`if (!RUNNING && !OFFLINE) continue;`），即 STOPPED 从不做可达性探测。
- 页面 `statusLabel()` 把 `STOPPED` 和 `OFFLINE` 都映射成"离线"：目前库中没有 OFFLINE 记录，所以"离线 281"实际等于"未启动拉流的设备数"，与运维人员理解的"设备离线/不可达"不是一回事。

## 四、附带观察（非本次结论）

- "从未连接成功"页签恒为 0：只有非 RUNNING/STOPPED/OFFLINE/DISABLED 的状态才会映射到该文案，而库里只存在 RUNNING/STOPPED 两种值。
- 首屏从导航到页签出现数字耗时约 32s，其中主要是客户端到现场链路的传输（当前构建 `assets/index-DNOSebMl.js` 1.48MB 下载约 46s、`/api/cameras` 433KB 约 20s），页面在拿到数据前会把五个页签都显示为 0，属测试链路带宽问题，非页面统计缺陷；同时需注意前端 30s 摄像头列表缓存（`CAMERAS_CACHE_TTL_MS`）内看到的是缓存值。
- 核验期间（约 20:20–20:40）前端容器被重新构建过（构建产物 hash 由 `index-DdVG-Z39.js` 变为 `index-DNOSebMl.js`），本报告数据均取自新构建。
- 历史报告中的设备总数（381 / 414）与当前 363 不同，说明期间做过增删；本次一律以当前库和当前页面为准。

## 五、复现命令

```bash
# 1. 库内总数与状态分布
ssh public@10.10.3.100 'cd /home/public/videoai && docker compose exec -T postgres \
  psql -U videoai -d videoai -At -F'|' \
  -c "SELECT status,count(*) FROM cameras GROUP BY status" -c "SELECT count(*) FROM cameras"'

# 2. 接口分布（8083 直连 / 5173 反代）
ssh public@10.10.3.100 'curl -fsS http://10.10.3.100:5173/api/cameras | python3 -c \
  "import sys,json,collections;d=json.load(sys.stdin);print(len(d),collections.Counter(c[\"status\"] for c in d))"'

# 3. 在线可信度：逐个拉 FLV / 查 ZLM 活动流
ssh public@10.10.3.100 'cd /home/public/videoai && set -a && . ./.env && set +a && \
  curl -fsS "http://10.10.3.100:82/index/api/getMediaList?secret=$ZLM_SECRET" | head -c 200'

# 4. 假在线设备的守护日志
ssh public@10.10.3.100 'cd /home/public/videoai && docker compose logs --since 1h backend-media | \
  grep -i "eafc6762" | tail -5'
```
