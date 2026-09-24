# 远程服务器部署说明

本文档记录当前远程服务器部署信息。后续部署按本文档执行。

## 服务器信息

- SSH 管理入口：`public@119.3.237.220 -p 3479`
- 新现场（172.21 网段，cisdi-4090-2）：`user@172.17.136.189`（端口 22，即 `.tools/remote_ssh.py` / `remote_sync.py` 的默认目标），项目目录 `/home/user/videoai`，端口绑定 `172.17.136.189`。ZLM 使用宿主机共享实例（zlmmediakit_main_1，`0.0.0.0:1935`/`0.0.0.0:81`），因此本项目 compose 的 zlm **不能绑定主机 1935**（已在远程 compose 注释，RTMP 推流走 `rtmp://172.17.136.189:1935/live` 到共享 ZLM）；`VIDEOAI_ZLM_HTTP_URL`/`VIDEOAI_ZLM_PUBLIC_HTTP_URL` 指向 `http://172.17.136.189:81`。CVR 中心存储 `172.21.200.21/22/23`（admin/Sdtjh@2025）经 `CVR_HOSTS`/`CVR_USERNAME`/`CVR_PASSWORD` 注入 mcp-server。**现场绝大多数摄像头是 CVR 直连 IPC，不要用平台字段判断能否回放**：2026-09-22 实测 904 路摄像头中 481 路的 `sourceUrl` IPC 已注册在 CVR 输入通道表里（三台 CVR 分别 182/225/119 路，合计 526 个输入通道），而这些摄像头在平台里的 `nvrTrackId`/`nvrChannel` **全为空**——录像检索/回放/下载必须先拿 `sourceUrl` 的 IPC 地址去反查 CVR 的 `InputProxy/channels` 得到真实通道（例如 `B1-1F-4#楼梯间出入口2` 的 IPC `172.21.111.11` → CVR `172.21.200.21` 通道 108 / trackId 10801）。只按 `nvrTrackId`/`nvrChannel` 过滤会得出"没有可回放摄像头"的错误结论。本现场视频理解接口（文搜视频 `/api/v1/video-understanding/structure`）在宿主机 `http://172.17.136.189:8780`，`.env` 已配 `VIDEO_ANALYSIS_API_BASE_URL` 与 `VIDEO_UNDERSTANDING_API_BASE_URL` 指向它（compose 默认的 `192.168.11.192:8775` 为开发网段，本现场不可达）。文搜图检索服务在宿主机 `http://172.17.136.189:15009`（`.env` 的 `RETRIEVE_API_BASE_URL`，compose 的 backend 与 mcp-server 均注入），图搜图（以图搜人）服务在宿主机 `http://172.17.136.189:15501`（`.env` 的 `PERSON_API_BASE_URL`），图搜图结果图片文档的 ES 查询接口（`/api/v1/queries/es-documents/by-ids`，mcp-query 服务）在宿主机 `http://172.17.136.189:15010`（`.env` 的 `ES_DOCUMENT_API_BASE_URL`，backend 注入；vlm-application v3 检索只回 es_ids，由 backend-lite 调该接口解析为完整人员文档）。
- 另一现场（10.10 网段）：`public@10.10.3.100`（端口 22），项目目录同为 `/home/public/videoai`，端口绑定与 `.env` 均使用 `10.10.3.100`，backend-media 绑定 `10.10.3.100:8083`。**仓库 `docker-compose.yml` 的绑定地址是 `192.168.11.194`，推送到 10.10 现场后必须立即执行 `sed -i "s/192\.168\.11\.194/10.10.3.100/g" docker-compose.yml`** 再重建容器，否则容器绑定不存在的地址无法启动。文搜图检索服务（retrieve 容器 `retrieve-py310-amd64`）实际监听宿主机 `http://10.10.3.100:15009`，`.env` 已配 `RETRIEVE_API_BASE_URL=http://10.10.3.100:15009`（compose 默认的 15000 无服务监听，2026-09-23 曾因此导致文搜图 502）；图搜图服务在 `http://10.10.3.100:15501`，ES 文档查询接口在 `http://10.10.3.100:15010`。ZLM 与 172 现场一样使用宿主机共享实例（`zlmmediakit_main_1`，占用 1935），本 compose 的 zlm 起不来，**mcp-server 依赖 zlm，启动必须加 `--no-deps`**（`docker compose up -d --no-deps mcp-server`），否则 compose 连带启动 zlm 报 1935 绑定冲突导致 mcp-server 起不来。**重建/重启 backend 容器后必须 `docker compose restart frontend frontend-control frontend-media frontend-review`**：前端 nginx 的 `proxy_pass http://backend:8081` 在启动时解析一次并缓存 IP，backend 重建后容器 IP 变化，不重启前端会导致所有 `/api` 请求返回 nginx 502 错误页（2026-09-23 实测踩坑）。
- 项目目录：`/home/public/videoai`
- 内网访问地址：`192.168.11.194`
- SSH 密码不写入仓库文档，按运维侧凭据管理。
- `.tools/remote_ssh.py` / `remote_sync.py` / `remote_push.py` 支持用 `VIDEOAI_DEPLOY_HOST` / `VIDEOAI_DEPLOY_PORT` / `VIDEOAI_DEPLOY_USER` / `VIDEOAI_DEPLOY_PASS` 环境变量切换目标服务器。

## 访问范围

本项目所有业务服务只允许内网访问，不对公网开放。Docker 端口必须绑定到 `192.168.11.194` 或 `127.0.0.1`，禁止使用 `0.0.0.0:端口:端口` 或省略 host IP 的 `端口:端口` 写法。

| 服务 | 内网地址 | 公网开放 |
| --- | --- | --- |
| Frontend（全量） | `http://192.168.11.194:5173/` | 否 |
| Frontend Media 子包 | `http://192.168.11.194:5175/` | 否 |
| Frontend Control 子包 | `http://192.168.11.194:5176/` | 否 |
| Frontend Review 子包 | `http://192.168.11.194:5177/` | 否 |
| SXin Proxy | `http://192.168.11.194:10997/` | 否 |
| Backend API（backend-lite） | `http://192.168.11.194:8081/` | 否 |
| Backend Media API（Java） | `http://192.168.11.194:8083/` | 否 |
| MCP Server | `http://192.168.11.194:8097/mcp` | 否 |
| PostgreSQL | `192.168.11.194:5434` | 否 |
| Worker | `http://192.168.11.194:18099/` | 否 |
| Triton（triton-docker-compose.yml，项目名 triton-deploy） | `192.168.11.194:8003-8005` | 否 |
| ZLM HTTP（启用时） | `http://192.168.11.194:8080/` | 否 |
| ZLM RTMP（启用时） | `rtmp://192.168.11.194:1935/live` | 否 |

公网 `119.3.237.220` 仅用于 SSH 管理入口，不作为业务服务访问地址。

## 当前部署约定

- Compose 文件：`/home/public/videoai/docker-compose.yml`
- 运行方式：Docker Compose
- 当前摄像头数据目录：`/home/public/videoai/storage/cameras`
- 当前摄像头数量：`23`
- SXin 助手代理：`192.168.11.194:10997` -> `192.168.11.192:9997`
- MCP 端口：`8097`
- MCP Python 依赖构建建议使用清华 PyPI 镜像，避免远程构建时依赖解析超时。

远程 `.env` 保留在服务器，不提交仓库。部署时沿用远程 `.env`，尤其是：

- `BACKEND_PUBLIC_URL=http://192.168.11.194:8081`
- `BACKEND_INTERNAL_URL=http://backend:8081`
- `ZLM_PUBLIC_HTTP_URL`、`ZLM_HTTP_URL`、`ZLM_RTMP_PUSH_BASE`
- `VIDEOAI_MCP_PUBLIC_BASE_URL`：录像动态链接（`/recording-live`）对外基址，必须是客户端可访问的 MCP 地址（10.10 现场为 `http://10.10.3.100:8097`）；compose 默认值的开发网段地址在现场不可达，会导致回放页/文搜返回的播放链接打不开
- `HIKVISION_NVR_BASE_URL=http://192.168.11.251`
- `VIDEOAI_MCP_RECORDING_FALLBACK_FILE=/data/demo-recording-601.ps`
- `VIDEOAI_MCP_RECORDING_FALLBACK_FILE_HOST=/home/public/videoai/demo-recording-601.ps`
- NVR、数据库等账号密码类配置

## 已知部署风险

- 服务器上其它项目容器已占用 `0.0.0.0:8082`（openclaw-middleware-zlmediakit）、`8000-8002`（zlmmediakit-main、openclaw 网关）等端口。本项目 backend-media 固定绑定 `192.168.11.194:8083`（远程 `.env` 的 `MEDIA_BACKEND_BIND` / `MEDIA_BACKEND_PUBLIC_URL`），禁止使用 8082。
- Triton 不由主 compose 启动（主 compose 的 triton 服务端口 8000-8002 与其它项目冲突）。使用 `docker compose -p triton-deploy -f triton-docker-compose.yml up -d`，端口 8003-8005，`.env` 的 `TRITON_HTTP_URL` / `TRITON_GRPC_URL` 指向 8003/8004。
- 人脸识别模型文件不入库：`retinaface_mobilenet` 与 `arcface_finetune` 的 `model.onnx` 从服务器 `/home/public/face_models_extract/` 拷贝到 `infra/model_repository/<model>/1/model.onnx`；`arcface_mbf`、`scrfd_10g` 已随仓库同步。

- 前端 API 请求一律走同源 nginx 反代（`/api/cameras`、`/api/live`、`/api/streams`、`/api/access-config`、`/api/cloud-platforms` → backend-media，其余 `/api/` → backend-lite），构建时禁止注入 `VITE_API_BASE_URL`/`VITE_MEDIA_API_BASE_URL` 绝对地址——浏览器直连 8081/8083 等后端端口在现网客户端链路上可能被限速（10.10 现场实测直连 8083 拉取设备列表需 24 秒+，走 5173 反代约 1 秒）。
- 实时预览和总览页的视频播放不要让浏览器直接依赖 ZLM 原始地址。普通摄像头应使用后端代理 `/api/live/{streamName}.live.flv`，DINO 物品识别摄像头使用后端 `/api/cameras/{cameraId}/annotated.mjpeg`，避免客户端网络无法直连视频流端口导致无画面。
- 后端重建或重启后，所有持久化状态为 `RUNNING` 的摄像头必须恢复 ZLM 流代理（现由 backend-media 负责）；DINO 摄像头还必须恢复 Worker 识别流。不要只依赖 30 秒定时守护线程做首次恢复。
- **设备状态两个维度必须分开看（2026-09-16 起，迁移 V16）**：`cameras.status` 只表示**拉流状态**（`RUNNING` 拉流中 / `STOPPED` 已停止 / `DISABLED` 停用），`cameras.online_status` 表示**设备可达性**（`ONLINE` / `OFFLINE` / `UNKNOWN` 未探测）。页面上的"在线/离线"一律指设备可达性；"拉流状态"单独展示（拉流中/拉流中断/已停止/停用/未启动）。历史 `status='OFFLINE'` 混用了两种语义，V16 已拆分为 `status=RUNNING + online_status=OFFLINE`。
- 设备可达性由 `CameraStatusScanService` 每 10 分钟对**全部设备**（含 STOPPED/DISABLED 与从未启动过的设备）的 `sourceUrl` 做 TCP 连接探测后写入 `online_status`（12 线程、单次 2 秒超时），不再改写拉流状态。需要立即重扫时执行 `curl -fsS -X POST http://10.10.3.100:8083/api/cameras/status-scan`（返回 `{total, online, offline, unknown, changed}`，同步等待整轮探测完成）。
- 拉流服务（ZLM `addStreamProxy`）拒绝地址时（如 `OPTIONS:404 Not Found`、`Unauthorized`），`CameraServiceImpl.start` 不再把设备置为 `RUNNING`，而是保持/回写 `STOPPED` 并返回 409；`StreamGuardServiceImpl` 对"设备可达但连续 3 次挂流失败"的设备也会把拉流状态降为 `STOPPED`，避免出现"页面显示拉流中但没有任何流"的假在线（设备本身 `OFFLINE` 时不降级，保留设备恢复后继续拉流的意图）。
- MCP `search_recordings` 返回 `url` 依赖 MCP 容器内的 `ffmpeg` 推流到 ZLM；MCP 镜像必须安装 `ffmpeg` 和 `procps`。当 NVR 返回 `453 Not Enough Bandwidth` 时，使用 `/data/demo-recording-601.ps` 回退文件生成 FLV/HLS 代理流，避免返回结果缺少录像视频流链接。
- 文搜视频链路：前端选定监控点+时段 → backend-lite `POST /api/video-analysis/recording-file`（透传 `cameraId` 与摄像头 `nvrTrackId`）→ MCP `export_recording`（优先 HCNetSDK 按时间下载为 MP4 上传 MinIO）→ 前端再调 `/api/video-analysis/analyze` 交给视频分析服务（`VIDEO_ANALYSIS_API_BASE_URL`）分析。**10.10 现场分析服务直连地址是宿主机 `http://10.10.3.100:8780`（原开发网段地址为 `192.168.11.192:8775`，`/analyze_minio_video` 无需认证，2026-09-16 实测空 body 返回 422 校验错误），现场 `.env` 已配 `VIDEO_ANALYSIS_API_BASE_URL=http://10.10.3.100:8780`**。注意 18888（宿主机 `backend-ai-platform` 容器）是 AI 平台网关，按会话认证，未带凭据时所有请求返回 `{"code":"401","message":"当前会话未登录"}`（HTTP 200 包裹），不要把它配成分析服务地址；`10.10.3.100:15501` 无服务监听（连接拒绝）。分析服务按 `videoUrl` 拉取视频文件，videoUrl 指向现场已绑定的 `cisdi-minio`（`10.10.3.100:9000`，`.env` 的 `MINIO_ENDPOINT`），两者同主机可互通。compose 的 backend 与 mcp-server 均注入 `MINIO_ENDPOINT`/`MINIO_PORT`/`MINIO_ACCESS_KEY`/`MINIO_SECRET_KEY`/`MINIO_BUCKET`（172.17 现场 MinIO 在宿主机 `29000` 端口，`.env` 已配 `MINIO_PORT=29000`；`/api/video-analysis/upload-video` 依赖 backend 的这组配置，缺省会连默认 9000 导致上传超时）。直连 IPC 摄像头由 MCP 端经 NVR 输入通道反查定位所属 NVR 与真实通道（平台 `nvrTrackId` 对直连 IPC 可能是脏数据，不作准）。只有绑定了 NVR track 的摄像头可用（远程 23 个摄像头中仅 3 个绑定：`1205会议室`→101、`1205会议室可控摄像头`→201、`金山12楼门口`→601）。导出自 2026-09 起默认走 HCNetSDK `NET_DVR_GetFileByTime` 按时间下载（非实时抓流，速度取决于网络带宽）：传 `cameraId` 时按摄像头 `sourceUrl` 内嵌凭据连接其绑定的 NVR/设备（多 NVR 路径，10.10 现场必须走此路径——现场 `.env` 的 `HIKVISION_NVR_BASE_URL=192.168.11.251` 在 10.10 网段不可达）；不传 `cameraId` 时按 `trackId` 对白名单 NVR 下载（trackId 换算 SDK 通道号），总上限 2 小时。白名单 trackId 路径下 SDK 下载不可用或失败时，20 分钟以内的时段自动回退 RTSP 回放抓流（约 1x 速度）；两侧都失败时报错同时包含两侧原因。
- 远程 NVR（192.168.11.251）为手动对时时钟，2026-08-31 实测比真实时间慢约 15 小时 40 分。其 RTSP 回放的 `starttime`/`endtime`（`Z` 后缀）按 NVR 本地时钟解释，且 `endtime` 不生效（需 ffmpeg `-t` 截断）。`export_recording` 已通过 `/ISAPI/System/time` 自动测量偏差并补偿；若现场校时后偏差为 0 则自动无影响。`/Streaming/tracks/{id}/` 尾斜杠必需；`/Streaming/Channels/{id}?starttime=...` 只会返回实时流边缘，不能用于回放导出。
- 浏览器实时预览通过 backend-media `/api/live/{streamName}.live.flv` 直接代理 ZLM 上的原始直播流，按摄像头源的原分辨率和编码播放，不经 ZLM `addFFmpegSource` ffmpeg 转码（`preview-{streamName}` 派生流已停用）。现场大部分摄像头为 H.265（ZLM 以 FLV CodecID 12 输出），前端 FLV 播放使用 mpegts.js（支持 H.264/H.265 passthrough，要求客户端浏览器支持 HEVC MSE，Windows Chrome 一般可用），不要使用 flv.js（仅支持 H.264）。
- 10.10 现场 ZLM `addStreamProxy` 拉 RTSP 必须走 TCP（`rtp_type=0`，2026-09-12 起 `ZlmClient.addStreamProxy` 已固定带上）：10.10.3.x → 10.10.7.x 跨网段 UDP 不通，默认 UDP 拉流会被 NVR 断开报 `end of file`。NVR252（10.10.7.252）有效通道范围 75–284，平台里引用通道 8、22–32 的 `NVR252通道*` 摄像头为错误配置（NVR 对不存在的通道直接断开 RTSP），已连同 22 路 192.168.11.x 开发网段遗留摄像头一并停用（备份 `backups/20260912-083701`）。
- MCP `search_recordings` 使用海康 NVR `192.168.11.251` 的 RTSP 回放地址构造录像流，返回新的录像 `url` 前必须清理 ZLM 中旧的 `rec-*`/`rec_*` 录像流。
- MCP `search_recordings` 构造海康 RTSP 回放地址时按东八区北京时间处理 `startTime`、`endTime`；未带时区的 ISO 时间也按北京时间解释，避免查询录像与现场时间相差 8 小时。ISAPI 检索同样如此：海康把 Z 后缀时间按设备本地时钟解释，检索窗口按北京时间墙钟发送（`format_hik_time`），返回的录像段时间也按北京时间墙钟解析（`parse_hik_time`），不得按 UTC 换算。
- 海康 NVR RTSP 回放会以高于实时的速度吐流，MCP 录像代理必须用 `ffmpeg -re` 做实时节流，并输出视频-only FLV，避免浏览器播放 `search_recordings` 返回的 `rec-*` 流时卡顿。SDK 点播回放（`hcn-*` 流）为不限速取流，倍速通过 `ffmpeg -readrate N` 限速 + `setpts=PTS/N` 时间戳压缩实现；现场 NVR（10.10.7.252/253）回放倍速实测支持 0.25/0.5/1/2/4/8/16/32 倍（32 倍以上返回 453）。
- MCP tools 的匿名 HTTP JSON 接口与 MCP 服务运行在同一端口，路径为 `/<mcp接口>-http`。录像动态播放链接 `GET /recording-live` 同样挂在该端口。这些接口无需认证，但仍只能内网访问，禁止因为 HTTP 匿名接口而把 `8097` 暴露到公网。
- SXin 助手 iframe 不要直接指向 `192.168.11.192:9997`。必须通过本项目 `sxin-proxy` 的 `192.168.11.194:10997` 访问，避免跨站 iframe 下浏览器拒绝 `Set-Cookie`。远程服务器已有非本项目服务占用 `0.0.0.0:9997`，禁止复用该端口。`sxin-proxy` 必须剥离 `Origin`、`Referer` 和 `X-Forwarded-*`，否则 SXin 登录接口会返回 `Cross-site auth request denied`。

- 设备管理页「区域管理 → 同步空间区域」（2026-09-24 新增）：backend-media 走 Feign 调空间服务 `GET /spatialServer/spatialInfo/tree?hasOther=true`，把园区/区域/楼栋/楼层按「同级同名」判重后**只新增**到 `regions` 表，已有区域结构（名称/排序/父子关系）一律不改动。空间服务基址可在区域管理弹窗里改，落库 `spatial_config` 单行表（迁移 V20）；`VIDEOAI_SPATIAL_BASE_URL` 只在库中未配置时兜底，默认 `http://172.17.2.131:8080`。接口不可访问/返回失败时后端只记 WARN 日志并返回 `success=false`（HTTP 200），不影响区域管理的其它操作。

### 录像回放页（对接现场 NVR，2026-09-04 新增）

- 前端录像回放页 → backend-lite `POST /api/recordings/search|stream|download`（body 均为 `{cameraId, startTime, endTime}`，北京时间）→ MCP `search_recordings-http` / `download_recording-http`（均支持 `cameraId`）；`/api/recordings/stream` 只调 `search_recordings-http`（autoProxy=true）取 `/recording-live` 动态链接并追加 `&speed=` 倍速参数。MCP 侧 `get_recording_stream` **不再作为 MCP tool**，但仍保留 `POST /get_recording_stream-http` 兼容入口：对缓存过的 `recordingId` 返回 **H.265 直通**流，只支持等速（`speed=1`）。
- 多 NVR 能力：MCP 按摄像头的 `nvrId`/`nvrTrackId`/`nvrChannel` 定位设备，凭据从摄像头 `sourceUrl`（`rtsp://user:pass@host:554/...`）解析，无需额外配置；ISAPI 检索录像段、HCNetSDK 按时间回放/下载，设备时钟偏差自动测量补偿。
- CVR 中心存储（DS-A80348S，如 172.21.200.21/22/23 集群）复用同一套反查机制：compose 注入 `CVR_HOSTS`/`CVR_USERNAME`/`CVR_PASSWORD`（CVR 凭据通常与 NVR 不同，`NvrChannelLookup` 按设备主机取专属凭据），直连 IPC 的摄像头回放/检索/下载时会反查 IPC→CVR 通道映射（CVR 的 `InputProxy/channels` 同样给出 IPC 地址与通道号），`CVR_HOSTS` 也并入 `known_nvr_hosts` 与下载白名单 `hcnetsdk_downloaders`。
- 录像设备列表按部署网段自动选择（2026-09-22 新增）：`HCNETSDK_DOWNLOAD_NVR_HOSTS`/`CVR_HOSTS` 置空（或不设置）时，mcp-server 按 `VIDEOAI_MCP_PUBLIC_BASE_URL` 主机网段取默认设备——10 网段（如 10.10.3.100 现场）→ 仅 NVR `10.10.7.252/253`；172 网段（如 cisdi-4090-2 现场）→ 仅 CVR `172.21.200.21/22/23`；未知网段兜底为两者全配（保持历史行为）并打告警日志。**反查会等每台配置设备的连接超时（15s），给某环境配了不可达的设备会把回放/检索拖慢 15s+（10.10 现场曾因误配 172 CVR 出现回放灰屏 20s）**；新环境在 `mcp-server/app/settings.py` 的 `_ENV_DEVICE_DEFAULTS` 追加映射行。
- 回放链路：SDK 回放 → ffmpeg `-re` 节流 + **libx264 转码**（现场 NVR 多为 smart265/HEVC，浏览器 flv.js 不支持，禁止改回 `-c:v copy`）→ ZLM FLV。等速流不支持倍速与真正的 seek，前端通过按新 startTime 重新起流实现跳转。ffmpeg 输入固定为 MPEG-PS（SDK 回调），已强制 `-f mpeg` 并限制 `-probesize 1000000 -analyzeduration 1000000`：`-re` 限速下 find_stream_info 会按实时速率分析输入，不限探测会拖慢首帧约 1.2s（2026-09-22 实测优化前 1713ms → 优化后 521ms）。输出固定 `-an` 无音轨（NVR 回放伴音是 G.711，浏览器无法解码）。
- 起播花屏与首帧等待（2026-09-22）：SDK 按请求时刻起播，起点常落在 GOP 中间，首个源 IDR 之前解码器只能输出掩盖花屏（smart265 长 GOP 下花屏可达 10s）。`PlaybackSession._write_ffmpeg_stdin` 起播 primer：先缓冲 PS 数据，`find_first_video_idr` 定位首个含 IDR/CRA（H.264 type5 / H.265 type 19/20/21）的视频 PES，从该 PES 起喂 ffmpeg，之前的数据丢弃；超过 16MB 无 IDR 兜底全量喂入。**代价是首帧前有一段静默期（等源关键帧，实测 4~12s）——期间 ZLM 连接已建立但无任何媒体数据，这是正常的，前端/客户端不得以「连接后 N 秒无画面」为由重连**：`VideoPlayer` 出帧看门狗以 mpegts `media_info`（真实视频数据到达）为武装时机，load 后 30s 无视频数据才兜底重连；过早重连会新建回放会话（每次重连都重新 primer），把一次慢起播放大成一分钟以上（实测 56~84s）。
- 浏览器播放 `/recording-live` 动态链接的两个硬性条件（2026-09-16 修复）：① MCP `GET /recording-live` 的 302/错误响应必须带 `Access-Control-Allow-Origin: *`（前端 5173 → 8097 跨源，302 第一跳无 CORS 头浏览器直接拦截；ZLM :82 自身会回 ACAO）；② 该链接不以 `.flv` 结尾，前端 `VideoPlayer` 只靠 URL 后缀识别 FLV 会落到原生 `<video>` 分支导致无法播放——录像回放三处调用（录像回放页、文搜在线回放、即时回放弹窗）必须显式传 `format="flv"` prop 走 mpegts.js。
- ISAPI 检索返回的是与查询窗口相交的**整个连续录像块**（海康设备行为，不裁剪）；MCP `search_segments` 会把结果裁剪到用户查询窗口（`clip_segment_to_window`），recordingId 随裁剪后的时间重算，避免不同窗口共享缓存键。
- SDK 点播回调为**不限速供流**（现场实测约 15MB/s ≈ 35 倍速），远超 ffmpeg 按倍速的消费速率；`PlaybackSession` 用队列高低水位 + `NET_DVR_PLAYPAUSE`/`PLAYRESTART` 做背压（实测该 NVR 支持暂停/续传且数据连续），禁止在队列满时丢块（破坏 PS 连续性 → 花屏或启流 ffmpeg 解复用失败）。`NET_DVR_PLAYSETSPEED` 在该 NVR 回调模式下不限速，不要用它做倍速。`ensure_playback` 起流失败（ffmpeg 偶发启流死亡）会重试至多 3 次。
- backend-lite 调 MCP 的地址由 compose 注入 `MCP_SERVER_BASE_URL`（默认 `http://mcp-server:8097` 走内网服务名），不要写死现场 IP（历史上默认值 `192.168.11.194:8097` 导致 10.10 现场 502）。
- 10.10 现场实测：381 路摄像头直连的单通道设备自身均无录像（ISAPI 检索 NO MATCHES）；有录像的是 NVR `10.10.7.252/253`（253 的 track 201 有录像）。回放页只对有录像的 NVR 通道有效，需先把 NVR 通道注册为平台摄像头（sourceUrl 用该 NVR 的管理员凭据）。
- 验证命令（10.10 现场，摄像头需绑定有录像的 NVR）：

```bash
curl -fsS -X POST http://10.10.3.100:8081/api/recordings/search \
  -H 'Content-Type: application/json' \
  -d '{"cameraId":"<id>","startTime":"<24h前>","endTime":"<现在>"}'
# 期望返回真实录像段列表；再调 /api/recordings/stream 取 FLV，
# ffprobe 确认 codec 为 h264；/api/recordings/download 返回 MinIO MP4（200 可下载）
```


## 部署步骤

1. 同步代码到远程项目目录。只同步本次变更涉及的文件或目录，禁止整仓 `--delete`，避免误删远程 `.env`、`storage/`、`backups/`。

前端变更：

```bash
rsync -az --delete \
  --exclude node_modules --exclude dist \
  -e 'ssh -p 3479 -o StrictHostKeyChecking=no' \
  frontend/ public@119.3.237.220:/home/public/videoai/frontend/
```

MCP 变更：

```bash
rsync -az --delete \
  --exclude .pytest_cache --exclude __pycache__ --exclude '*.pyc' \
  -e 'ssh -p 3479 -o StrictHostKeyChecking=no' \
  mcp-server/ public@119.3.237.220:/home/public/videoai/mcp-server/
```

backend-lite 变更：

```bash
rsync -az --delete \
  --exclude .pytest_cache --exclude .mypy_cache --exclude .ruff_cache --exclude __pycache__ --exclude '*.pyc' \
  -e 'ssh -p 3479 -o StrictHostKeyChecking=no' \
  backend-lite/ public@119.3.237.220:/home/public/videoai/backend-lite/
```

Compose、infra 或文档变更：

```bash
rsync -az -e 'ssh -p 3479 -o StrictHostKeyChecking=no' \
  docker-compose.yml README.md \
  public@119.3.237.220:/home/public/videoai/
rsync -az -e 'ssh -p 3479 -o StrictHostKeyChecking=no' \
  infra/sxin-proxy/ \
  public@119.3.237.220:/home/public/videoai/infra/sxin-proxy/
rsync -az -e 'ssh -p 3479 -o StrictHostKeyChecking=no' \
  docs/remote-deployment.md docs/mcp-server-interface.md \
  public@119.3.237.220:/home/public/videoai/docs/
```

2. 前端变更部署（全量 + 3 个子包）：

```bash
ssh -p 3479 public@119.3.237.220 \
  'cd /home/public/videoai && docker compose build frontend frontend-media frontend-control frontend-review && docker compose up -d --no-deps frontend frontend-media frontend-control frontend-review'
```

3. backend-lite（Python 后端，容器名 backend，端口 8081）/ worker 变更部署：

```bash
ssh -p 3479 public@119.3.237.220 \
  'cd /home/public/videoai && docker compose build backend worker && docker compose up -d --no-deps backend worker'
```

4. SXin 代理变更部署：

```bash
ssh -p 3479 public@119.3.237.220 \
  'cd /home/public/videoai && docker compose up -d --no-deps sxin-proxy'
```

5. MCP 变更部署：

```bash
ssh -p 3479 public@119.3.237.220 \
  'cd /home/public/videoai && docker compose build --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple mcp-server && docker compose up -d --no-deps mcp-server'
```

6. 仅端口、环境或 Compose 配置变更时，按需重建容器，不重建镜像：

```bash
ssh -p 3479 public@119.3.237.220 \
  'cd /home/public/videoai && docker compose up -d --no-deps --no-build postgres backend backend-media frontend frontend-media frontend-control frontend-review worker mcp-server sxin-proxy'
```

注意统一使用 `--no-deps`：主 compose 的 `zlm` 服务端口与服务器上已有的其它项目容器冲突，不能让 compose 顺带拉起它。

Java backend-media（`backend/` 多模块 Maven 工程）变更：

```bash
ssh -p 3479 public@119.3.237.220 \
  'cd /home/public/videoai && docker compose build backend-media && docker compose up -d --no-deps backend-media'
```

涉及 `storage/`、数据库、摄像头配置或后端持久化逻辑的变更，先备份：

```bash
ssh -p 3479 public@119.3.237.220 \
  'cd /home/public/videoai && ts=$(date +%Y%m%d-%H%M%S) && mkdir -p backups/$ts && cp -a storage/cameras backups/$ts/'
```

## 验证

部署后必须检查本项目服务状态、内网端口绑定和公网不可达。

```bash
ssh -p 3479 public@119.3.237.220 \
  'cd /home/public/videoai && docker compose ps'
```

预期本项目服务端口只显示 `192.168.11.194:端口->容器端口` 或 `127.0.0.1:端口->容器端口`，不能显示 `0.0.0.0:端口->容器端口`。

```bash
ssh -p 3479 public@119.3.237.220 \
  "ss -ltnp | grep -E ':(5173|8081|8097|5434|18099|10997)' || true"
```

预期本项目常驻端口监听只出现 `192.168.11.194:端口` 或 `127.0.0.1:端口`，不能出现 `0.0.0.0:端口`。服务器上可能存在非本项目容器占用其他端口，不作为本项目部署验收依据。

```bash
curl --max-time 5 http://119.3.237.220:8097/mcp
```

预期公网访问超时或拒绝。MCP 内部功能验证：

```bash
curl --max-time 5 http://119.3.237.220:10997/iot-os/sxin/
```

预期公网访问超时或拒绝。SXin 内网代理验证：

```bash
ssh -p 3479 public@119.3.237.220 \
  'curl -fsSI http://192.168.11.194:10997/iot-os/sxin/ | head -n 1'
```

预期返回 `HTTP/1.1 200 OK`。

```bash
ssh -p 3479 public@119.3.237.220 \
  'cd /home/public/videoai && docker compose exec -T mcp-server python - <<'"'"'PY'"'"'
import asyncio
from app.server import list_cameras
result = asyncio.run(list_cameras())
print(len(result["data"]), result["total"], result["page"], result["pageSize"])
first = result["data"][0]
print(sorted(first.keys()))
print("url=" in result["xml"])
PY'
```

MCP 海康 NVR 配置验证：

```bash
ssh -p 3479 public@119.3.237.220 \
  'cd /home/public/videoai && docker compose exec -T mcp-server python - <<'"'"'PY'"'"'
from app.settings import load_settings
s = load_settings()
print(s.hikvision_base_url)
print(s.hikvision_username)
print(bool(s.hikvision_password))
PY'
```

预期地址为 `http://192.168.11.251`，账号非空，密码只验证是否已配置，不打印密码。

MCP 录像代理依赖验证：

```bash
ssh -p 3479 public@119.3.237.220 \
  'cd /home/public/videoai && docker compose exec -T mcp-server sh -lc "command -v ffmpeg && command -v pkill && test -s /data/demo-recording-601.ps"'
```

`ffmpeg` 缺失时 `search_recordings` 无法生成 `url`。NVR 忙或带宽不足返回 `453` 时，会使用 `/data/demo-recording-601.ps` 生成演示录像流。

摄像头数量验证（`/api/cameras` 已迁移到 backend-media 8083，backend-lite 8081 不再提供该接口）：

```bash
ssh -p 3479 public@119.3.237.220 \
  'curl -fsS http://192.168.11.194:8083/api/cameras | python3 -c "import sys,json; print(len(json.load(sys.stdin)))"'
```

设备在线状态验证（2026-09-16 起两个维度分开统计；扫描覆盖全部设备）：

```bash
ssh public@10.10.3.100 'cd /home/public/videoai && \
  curl -fsS -X POST http://10.10.3.100:8083/api/cameras/status-scan && echo && \
  docker compose exec -T postgres psql -U videoai -d videoai -At -F"|" \
    -c "SELECT coalesce(online_status,'<null>'), count(*) FROM cameras GROUP BY 1" \
    -c "SELECT status, count(*) FROM cameras GROUP BY 1"'
```

预期：`online_status` 的合计等于设备总数（可达设备为 `ONLINE`，不可达为 `OFFLINE`，地址不可解析/内部推流为 `UNKNOWN`）；`status` 仍只有 `RUNNING/STOPPED/DISABLED`。

前端 API 代理验证（前端为构建产物，`/api/cameras`、`/api/live`、`/api/streams`、`/api/access-config` 由前端 nginx 反代到 backend-media，其余 `/api/` 反代到 backend-lite）：

```bash
ssh -p 3479 public@119.3.237.220 \
  'curl -fsS http://192.168.11.194:5173/api/health && curl -fsS -o /dev/null -w "%{http_code}\n" http://192.168.11.194:5173/api/cameras'
```

预期两个请求都返回 200。前端 API 请求为同源相对路径，全部经 nginx 反代；构建产物中不应再出现 `8081`/`8083` 的绝对后端地址（可用 `curl -s http://<前端>/assets/index-*.js | grep -c ':8083'` 验证为 0）。

实时视频流验证（`/api/live` 已迁移到 backend-media 8083）：

```bash
ssh -p 3479 public@119.3.237.220 \
  'for name in nvr65 nvr198; do out=/tmp/$name.flv; rm -f $out; curl --max-time 5 -sS http://192.168.11.194:8083/api/live/$name.live.flv -o $out; printf "%s bytes=%s head=" "$name" "$(wc -c < $out 2>/dev/null || echo 0)"; head -c 4 $out | xxd -p; rm -f $out; done'
```

预期 FLV 流头为 `464c5601`，且超时前已收到视频数据。

DINO 标注流验证：

```bash
ssh -p 3479 public@119.3.237.220 \
  'curl -fsS http://192.168.11.194:18099/v1/streams'
```

预期 DINO（`192.168.11.65`）与人脸识别摄像头的 Worker 流状态为 `running`。再抽样访问 backend-media `/api/cameras/{cameraId}/annotated.mjpeg`（`http://192.168.11.194:8083`），应能收到以 `--frame` 开头的 MJPEG 数据。
