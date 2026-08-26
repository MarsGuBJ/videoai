# 远程服务器部署说明

本文档记录当前远程服务器部署信息。后续部署按本文档执行。

## 服务器信息

- SSH 管理入口：`public@119.3.237.220 -p 3479`
- 项目目录：`/home/public/videoai`
- 内网访问地址：`192.168.11.194`
- SSH 密码不写入仓库文档，按运维侧凭据管理。

## 访问范围

本项目所有业务服务只允许内网访问，不对公网开放。Docker 端口必须绑定到 `192.168.11.194` 或 `127.0.0.1`，禁止使用 `0.0.0.0:端口:端口` 或省略 host IP 的 `端口:端口` 写法。

| 服务 | 内网地址 | 公网开放 |
| --- | --- | --- |
| Frontend（全量） | `http://192.168.11.194:5173/` | 否 |
| Frontend Search 子包 | `http://192.168.11.194:5174/` | 否 |
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
- `HIKVISION_NVR_BASE_URL=http://192.168.11.251`
- `VIDEOAI_MCP_RECORDING_FALLBACK_FILE=/data/demo-recording-601.ps`
- `VIDEOAI_MCP_RECORDING_FALLBACK_FILE_HOST=/home/public/videoai/demo-recording-601.ps`
- NVR、数据库等账号密码类配置

## 已知部署风险

- 服务器上其它项目容器已占用 `0.0.0.0:8082`（openclaw-middleware-zlmediakit）、`8000-8002`（zlmmediakit-main、openclaw 网关）等端口。本项目 backend-media 固定绑定 `192.168.11.194:8083`（远程 `.env` 的 `MEDIA_BACKEND_BIND` / `MEDIA_BACKEND_PUBLIC_URL`），禁止使用 8082。
- Triton 不由主 compose 启动（主 compose 的 triton 服务端口 8000-8002 与其它项目冲突）。使用 `docker compose -p triton-deploy -f triton-docker-compose.yml up -d`，端口 8003-8005，`.env` 的 `TRITON_HTTP_URL` / `TRITON_GRPC_URL` 指向 8003/8004。
- 人脸识别模型文件不入库：`retinaface_mobilenet` 与 `arcface_finetune` 的 `model.onnx` 从服务器 `/home/public/face_models_extract/` 拷贝到 `infra/model_repository/<model>/1/model.onnx`；`arcface_mbf`、`scrfd_10g` 已随仓库同步。

- 前端构建和运行必须优先使用远程 `.env` 中的 `BACKEND_PUBLIC_URL=http://192.168.11.194:8081`。即使通过 `127.0.0.1` 或 `localhost` 访问前端页面，也不能把 API 自动改成访问浏览器本机 `127.0.0.1:8081`，否则设备管理页会显示摄像头消失。
- 实时预览和总览页的视频播放不要让浏览器直接依赖 ZLM 原始地址。普通摄像头应使用后端代理 `/api/live/{streamName}.live.flv`，DINO 物品识别摄像头使用后端 `/api/cameras/{cameraId}/annotated.mjpeg`，避免客户端网络无法直连视频流端口导致无画面。
- 后端重建或重启后，所有持久化状态为 `RUNNING` 的摄像头必须恢复 ZLM 流代理（现由 backend-media 负责）；DINO 摄像头还必须恢复 Worker 识别流。不要只依赖 30 秒定时守护线程做首次恢复。
- MCP `search_recordings` 返回 `url` 依赖 MCP 容器内的 `ffmpeg` 推流到 ZLM；MCP 镜像必须安装 `ffmpeg` 和 `procps`。当 NVR 返回 `453 Not Enough Bandwidth` 时，使用 `/data/demo-recording-601.ps` 回退文件生成 FLV/HLS 代理流，避免返回结果缺少录像视频流链接。
- 浏览器实时预览通过 backend-media `/api/live/{streamName}.live.flv` 按需创建独立的 `preview-{streamName}` H.264 流。原始 ZLM 流保持不变，供算法和其他内部消费者继续使用。
- 按需预览状态保存在 backend-media 进程内，因此生产环境 backend-media 必须保持单实例运行。最后一个观看者断开 60 秒后，后端调用 ZLM `delFFmpegSource` 清理转码进程。

### ZLMediaKit 按需 H.264 预览配置

远端 ZLM 配置文件为 `/data/cloud-edge-platform/midware/zlmmediakit/config.ini`。在现有 `[ffmpeg]` 段增加以下唯一键，不替换默认 `cmd`：

```ini
cmd_preview_h264=%s -rtsp_transport tcp -i %s -an -c:v libx264 -preset ultrafast -tune zerolatency -pix_fmt yuv420p -g 50 -keyint_min 50 -sc_threshold 0 -f flv %s
```

后端使用 `ffmpeg_cmd_key=ffmpeg.cmd_preview_h264` 调用 ZLM `addFFmpegSource`。部署后应执行以下检查：

1. 打开一路实时预览，确认 `listFFmpegSource` 和 `getMediaList` 中仅出现一个对应的 `preview-{streamName}`。
2. 使用 `ffprobe` 检查 `http://10.10.3.100:82/live/preview-{streamName}.live.flv`，视频编码必须为 `h264`。
3. 同一路打开两个播放器，ZLM FFmpeg source 数量仍应为一个。
4. 关闭全部播放器并等待 60 秒及少量调度余量，确认 FFmpeg source、派生媒体流和 FFmpeg 进程均已移除。
5. 检查后端与 ZLM 日志，确保未输出摄像头 RTSP 凭据或 ZLM API 密钥。
- MCP `search_recordings` 使用海康 NVR `192.168.11.251` 的 RTSP 回放地址构造录像流，返回新的录像 `url` 前必须清理 ZLM 中旧的 `rec-*`/`rec_*` 录像流。
- MCP `search_recordings` 构造海康 RTSP 回放地址时按东八区北京时间处理 `startTime`、`endTime`；未带时区的 ISO 时间也按北京时间解释，避免查询录像与现场时间相差 8 小时。
- 海康 NVR RTSP 回放会以高于实时的速度吐流，MCP 录像代理必须用 `ffmpeg -re` 做实时节流，并输出视频-only FLV，避免浏览器播放 `search_recordings` 返回的 `rec-*` 流时卡顿。
- MCP tools 的匿名 HTTP JSON 接口与 MCP 服务运行在同一端口，路径为 `/<mcp接口>-http`。这些接口无需认证，但仍只能内网访问，禁止因为 HTTP 匿名接口而把 `8097` 暴露到公网。
- SXin 助手 iframe 不要直接指向 `192.168.11.192:9997`。必须通过本项目 `sxin-proxy` 的 `192.168.11.194:10997` 访问，避免跨站 iframe 下浏览器拒绝 `Set-Cookie`。远程服务器已有非本项目服务占用 `0.0.0.0:9997`，禁止复用该端口。`sxin-proxy` 必须剥离 `Origin`、`Referer` 和 `X-Forwarded-*`，否则 SXin 登录接口会返回 `Cross-site auth request denied`。

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

2. 前端变更部署（全量 + 4 个子包）：

```bash
ssh -p 3479 public@119.3.237.220 \
  'cd /home/public/videoai && docker compose build frontend frontend-search frontend-media frontend-control frontend-review && docker compose up -d --no-deps frontend frontend-search frontend-media frontend-control frontend-review'
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
  'cd /home/public/videoai && docker compose up -d --no-deps --no-build postgres backend backend-media frontend frontend-search frontend-media frontend-control frontend-review worker mcp-server sxin-proxy'
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
print(len(result["data"]))
first = result["data"][0]
print("url" in first, "livePlaybackUrl" in first, first["url"] == first["livePlaybackUrl"])
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

前端 API 代理验证（前端为构建产物，`/api/cameras`、`/api/live`、`/api/streams`、`/api/access-config` 由前端 nginx 反代到 backend-media，其余 `/api/` 反代到 backend-lite）：

```bash
ssh -p 3479 public@119.3.237.220 \
  'curl -fsS http://192.168.11.194:5173/api/health && curl -fsS -o /dev/null -w "%{http_code}\n" http://192.168.11.194:5173/api/cameras'
```

预期两个请求都返回 200。前端构建必须使用远程 `.env` 的 `BACKEND_PUBLIC_URL=http://192.168.11.194:8081`；即使通过 `127.0.0.1` 或 `localhost` 访问前端页面，也不能把 API 自动改成访问浏览器本机 `127.0.0.1:8081`，否则设备管理页会显示摄像头消失。

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
