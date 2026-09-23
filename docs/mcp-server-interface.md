# VideoAI MCP Server 接口说明书

## 1. 概述

VideoAI MCP Server 用于向 MCP 客户端暴露视频监控与检索能力：

- 查询 VideoAI 摄像头列表。
- 获取指定摄像头实时视频播放地址。
- 查询海康 NVR 历史录像并生成短期 FLV 回放流。
- 下载/导出 NVR 录像为 MP4 文件（MinIO）。
- 视频智能分析（按提示词分析视频文件，文搜视频）。
- 文搜图（自然语言检索人员/车辆图片）、图搜图（以图搜人）。
- 人员检测、以图搜人分步接口、步态比对、人脸布控、DINO 物品识别事件。

视频字节流不通过 MCP 协议传输。MCP tools 只返回播放/文件 URL，实际播放与下载由 HTTP/ZLMediaKit/MinIO 等媒体服务完成。

多数 tool 同时返回 `data`（JSON 结构化数据）和 `xml`（`sxin-*` 格式摘要，供 AI 代理解析展示）；各节示例以 `data` 为主。

`xml` 字段的内容**不含** `<?xml version="1.0" encoding="UTF-8"?>` 声明，直接以根元素开头（例如 `<sxin-camera-list ...>`），便于嵌入拼接；需要声明的消费方自行补上即可。

## 2. 服务信息

默认服务名：

```text
videoai-monitoring
```

默认 MCP 入口：

```text
http://192.168.11.194:8097/mcp
```

同一服务内还提供匿名 HTTP JSON 入口，路径为 `/<mcp接口>-http`。HTTP 接口使用 `POST`，请求体为 JSON object，功能和同名 MCP tool 一致。少数接口只有 HTTP 入口、不注册为 MCP tool，已在名称后标注。

```text
http://192.168.11.194:8097/list_cameras-http
http://192.168.11.194:8097/get_live_stream-http
http://192.168.11.194:8097/search_recordings-http
http://192.168.11.194:8097/get_recording_stream-http   # 仅 HTTP，返回 H.265 直通流
http://192.168.11.194:8097/download_recording-http
http://192.168.11.194:8097/export_recording-http
http://192.168.11.194:8097/video_understanding-http
http://192.168.11.194:8097/text_search_images-http
http://192.168.11.194:8097/search_person_by_image-http
http://192.168.11.194:8097/upload_face_image-http
http://192.168.11.194:8097/query_face_matches-http
http://192.168.11.194:8097/detect_persons-http
http://192.168.11.194:8097/search_person_by_bbox-http
http://192.168.11.194:8097/get_person_search_result-http
http://192.168.11.194:8097/detect_persons_with_id-http
http://192.168.11.194:8097/get_person_bbox-http
http://192.168.11.194:8097/gait_feature_compare-http
http://192.168.11.194:8097/dino_events-http
```

默认传输方式：

```text
streamable-http
```

可选传输方式由 `VIDEOAI_MCP_TRANSPORT` 配置，当前实现支持 FastMCP 的 `stdio`、`sse`、`streamable-http`。

## 3. 依赖服务

MCP Server 依赖以下服务：

- VideoAI Backend（backend-media）：读取摄像头列表、获取摄像头详情、启动直播。
- Person API：封装 `192.168.11.192:18890` 的图搜人和步态识别接口。
- 文搜图检索服务：`192.168.11.194:15011` 的自然语言图片检索接口（`text_search_images`）。
- 视频理解结构化展示服务：`10.10.3.100:8780` 的视频理解结构化接口（`video_understanding`，上游为 `POST /api/v1/video-understanding/structure`）。
- ZLMediaKit：把海康回放码流转为 FLV/HLS 播放地址。
- 海康 NVR / HCNetSDK 设备：`search_recordings` 的 SDK 回放、`download_recording` 的 SDK 下载、`export_recording` 的 SDK 按时间下载（RTSP 回放抓流兜底）。
- MinIO：保存 `download_recording` / `export_recording` 生成的 MP4 文件。

## 4. 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `VIDEOAI_BACKEND_URL` | `http://localhost:8081` | VideoAI 后端地址。Docker Compose 中默认为 `http://backend:8081`。 |
| `VIDEOAI_MEDIA_BACKEND_URL` | 空（回退 `VIDEOAI_BACKEND_URL`） | Java backend-media 地址，摄像头列表/直播实际来源；Compose 中为 `http://backend-media:8081`。 |
| `PERSON_API_BASE_URL` | `http://192.168.11.192:18890` | 图搜人和步态识别上游服务地址。 |
| `RETRIEVE_API_BASE_URL` | `http://192.168.11.194:15011` | 文搜图（自然语言图片检索）上游服务地址。 |
| `RETRIEVE_API_TIMEOUT_SECONDS` | `120` | 文搜图检索请求超时时间，单位秒。 |
| `VIDEO_UNDERSTANDING_API_BASE_URL` | `http://10.10.3.100:8780` | 视频理解结构化展示服务地址（`video_understanding`，上游 `POST /api/v1/video-understanding/structure`）。 |
| `VIDEO_UNDERSTANDING_TIMEOUT_SECONDS` | `600` | 视频理解结构化请求超时时间，单位秒。 |
| `VIDEOAI_ZLM_HTTP_URL` | `http://127.0.0.1:8082` | ZLMediaKit 内部 API 地址。 |
| `VIDEOAI_ZLM_PUBLIC_HTTP_URL` | `http://192.168.11.194:9100` | 返回给客户端的播放地址前缀，应配置为客户端所在网络可访问的 ZLMediaKit HTTP 地址。 |
| `VIDEOAI_ZLM_SECRET` | 项目默认 secret | ZLMediaKit API secret。 |
| `VIDEOAI_ZLM_RTMP_PUSH_BASE` | `rtmp://127.0.0.1:1945/live` | 转推历史回放流的 RTMP 目标前缀。 |
| `VIDEOAI_MCP_RECORDING_FALLBACK_FILE` | 空 | NVR 返回 `453 Not Enough Bandwidth` 时用于生成演示回放流的本地录像文件路径（容器内路径）。 |
| `VIDEOAI_MCP_PUBLIC_BASE_URL` | `http://192.168.11.194:8097` | 生成 `/recording-live` 动态播放链接的对外基址，必须与客户端实际可访问的 MCP 地址一致。 |
| `HIKVISION_NVR_BASE_URL` | 空 | 海康 NVR 地址，例如 `http://192.168.1.64`。 |
| `HIKVISION_NVR_USERNAME` | 空 | 海康 NVR 用户名。 |
| `HIKVISION_NVR_PASSWORD` | 空 | 海康 NVR 密码。 |
| `HCNETSDK_HOST` | `192.168.11.198` | HCNetSDK 私有协议录像设备地址。 |
| `HCNETSDK_PORT` | `8000` | HCNetSDK 私有协议端口。 |
| `HCNETSDK_USERNAME` | `admin` | HCNetSDK 登录用户名。 |
| `HCNETSDK_PASSWORD` | `cisdi123` | HCNetSDK 登录密码。 |
| `HCNETSDK_CHANNEL` | `1` | 默认录像通道。 |
| `HCNETSDK_MAX_LIVE_SESSIONS` | `0` | 每台设备同时保持的 SDK 回放会话上限；`0` 表示不限制。仅为 NVR 回放并发受限的特定部署环境（如 demo 环境）设置，例如 `2`。 |
| `HCNETSDK_DEVICE_PORT` | `8000` | cameraId 多 NVR 路径下各摄像头绑定设备的 HCNetSDK 端口。 |
| `HCNETSDK_DOWNLOAD_NVR_HOSTS` | 按部署网段 | `download_recording` 允许选择的 NVR 名称/IP，使用逗号分隔。置空（或不设置）时按 MCP 对外基址（`VIDEOAI_MCP_PUBLIC_BASE_URL`）的网段自动选择：10 网段 → `10.10.7.252,10.10.7.253`，172 网段 → 空（只用 CVR）；未知网段兜底为 `10.10.7.252,10.10.7.253`。新环境在 `app/settings.py` 的 `_ENV_DEVICE_DEFAULTS` 追加映射。 |
| `CVR_HOSTS` | 按部署网段 | CVR 中心存储集群地址，逗号分隔。置空（或不设置）时按部署网段自动选择：10 网段 → 空，172 网段 → `172.21.200.21,172.21.200.22,172.21.200.23`；未知网段兜底同 172 网段。 |
| `HCNETSDK_DOWNLOAD_PORT` | `8000` | 录像下载设备的 HCNetSDK 端口。 |
| `HCNETSDK_DOWNLOAD_USERNAME` | `admin` | 录像下载设备共用的登录用户名。 |
| `HCNETSDK_DOWNLOAD_PASSWORD` | 空 | 录像下载设备共用的登录密码，必须通过部署环境配置。 |
| `HCNETSDK_DOWNLOAD_CHANNEL` | `1` | 录像下载设备共用的通道。 |
| `MINIO_ENDPOINT` | `192.168.11.194` | MinIO 服务地址。 |
| `MINIO_PORT` | `9000` | MinIO 服务端口。 |
| `MINIO_USE_SSL` | `false` | 是否使用 HTTPS 访问 MinIO。 |
| `MINIO_ACCESS_KEY` | `minio` | MinIO access key。 |
| `MINIO_SECRET_KEY` | `Klg4dM9F3H` | MinIO secret key。 |
| `MINIO_BUCKET` | `public` | MP4 文件保存 bucket。 |
| `VIDEOAI_MCP_PLAYBACK_TTL_SECONDS` | `1800` | 历史录像缓存和播放 URL 的默认有效期，单位秒。 |
| `VIDEOAI_MCP_REQUEST_TIMEOUT_SECONDS` | `15` | 外部 HTTP 请求超时时间，单位秒。 |
| `VIDEOAI_MCP_HOST` | `0.0.0.0` | MCP Server 容器内监听地址；宿主机只绑定 `192.168.11.194:8097`，不对公网开放。 |
| `VIDEOAI_MCP_PORT` | `8097` | MCP Server 监听端口。 |
| `VIDEOAI_MCP_TRANSPORT` | `streamable-http` | MCP 传输方式。 |
| `CAMERA_IMPORT_USERNAME` | 空 | 摄像头批量导入 CLI（`camera_import`）使用的平台账号，非 MCP tool 运行时路径。 |
| `CAMERA_IMPORT_PASSWORD` | 空 | 摄像头批量导入 CLI 使用的平台密码，未配置时导入工具报 `camera import credentials are not configured`。 |

## 5. 摄像头 NVR 绑定字段

历史录像相关能力依赖摄像头上的 NVR 绑定信息。摄像头对象有以下可选字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `nvrId` | `string|null` | NVR 标识，用于区分设备或做展示。 |
| `nvrChannel` | `string|null` | NVR 通道号。未配置 `nvrTrackId` 时可作为查询 track ID 使用。 |
| `nvrTrackId` | `string|null` | 海康 NVR 回放 track ID，优先级高于 `nvrChannel`；`export_recording` 即按它定位回放通道。 |
| `nvrStreamType` | `string|null` | 码流类型，例如 `main`、`sub`，当前主要用于元数据返回。 |

当前客户演示环境：NVR 为 `192.168.11.251`（`export_recording` 按 `nvrTrackId` 导出）；`search_recordings` 不传 `cameraId` 时的 SDK 回放设备由 `HCNETSDK_HOST`/`HCNETSDK_CHANNEL` 决定（默认 `192.168.11.198` 通道 1）；传入 `cameraId` 时按该摄像头 `sourceUrl` 内嵌凭据连接其绑定的 NVR（多 NVR 路径，见 6.3）。

## 6. Tools

以下 MCP tools 均有对应 HTTP JSON 接口，接口名为 `/<tool名称>-http`，例如 `search_recordings` 对应 `/search_recordings-http`。HTTP 成功响应直接返回同名 MCP tool 的 JSON 结果；参数错误返回 `400` JSON，服务端异常返回 `500` JSON。

### 6.1 `list_cameras`

查询 VideoAI 后端中配置的摄像头列表。

#### 输入参数

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `name` | `string` | `""` | 按摄像头名称做大小写不敏感的子串过滤；为空则不过滤。 |
| `page` | `integer` | `1` | 页码，从 1 开始；小于 1 时按 1 处理。 |
| `pageSize` | `integer` | `20` | 每页条数，上限 `200`。 |

#### 返回值

返回 `data`（当前页摄像头数组，不含仅作 NVR 录像通道、无直播源的设备）、`total`（过滤后的总条数）、`page`、`pageSize` 和 `xml`（`sxin-camera-list` 摘要）。名称过滤先于分页，`total` 为过滤后的总数，不受分页影响。

```json
{
  "data": [
    {
      "id": "6f1d3f34-7ab1-4d7e-9f1e-f3d0a7b9c101",
      "status": "RUNNING",
      "url": "http://192.168.11.194:81/live/camera1.live.flv",
      "name": "Gate Camera"
    }
  ],
  "total": 1,
  "page": 1,
  "pageSize": 20,
  "xml": "<sxin-camera-list count=\"1\">...</sxin-camera-list>"
}
```

#### 字段说明

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `string` | 摄像头 ID，作为 `cameraId` 传给 `get_live_stream`、`search_recordings`、`export_recording` 等接口。 |
| `status` | `string` | 设备在线状态：`RUNNING` = 在线，`STOPPED` = 离线（取自后端 `onlineStatus`，非拉流状态）。 |
| `name` | `string` | 摄像头名称。 |
| `url` | `string` | 实时流播放地址。 |
| `total` | `integer` | 过滤后的摄像头总数（不受分页影响）。 |
| `page` | `integer` | 当前页码。 |
| `pageSize` | `integer` | 当前每页条数。 |

> 需要摄像头的原始 `sourceUrl`、NVR 绑定等信息时，走 backend-lite 的 `/api/cameras` 接口；`list_cameras` 只返回上表字段。

### 6.2 `get_live_stream`

获取某一路摄像头的实时视频播放地址。

#### 输入参数

```json
{
  "cameraId": "6f1d3f34-7ab1-4d7e-9f1e-f3d0a7b9c101",
  "autoStart": true
}
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `cameraId` | `string` | 是 | 无 | 摄像头 ID。 |
| `autoStart` | `boolean` | 否 | `true` | 摄像头非运行状态时是否调用后端启动直播。 |

#### 返回值

返回播放地址信息，并附 `xml`（`sxin-camera-flow` 摘要）字段；`input` 字段原样回显本次调用的输入参数（`cameraId`、`autoStart`）。

```json
{
  "url": "http://192.168.11.194:81/live/camera1.live.flv",
  "format": "flv",
  "expiresAt": null,
  "source": "live",
  "metadata": {
    "cameraId": "6f1d3f34-7ab1-4d7e-9f1e-f3d0a7b9c101",
    "cameraName": "Gate Camera",
    "status": "RUNNING",
    "streamApp": "live",
    "streamName": "camera1"
  },
  "xml": "<sxin-camera-flow>...</sxin-camera-flow>"
}
```

#### `format` 取值

当前根据 URL 自动识别：

- `hls`：URL 以 `.m3u8` 结尾。
- `flv`：URL 以 `.flv` 结尾。
- `mjpeg`：URL 以 `.mjpeg` 结尾。
- `rtsp`：URL 以 `rtsp://` 开头。
- `url`：其他 URL。

### 6.3 `search_recordings`

通过 HCNetSDK 私有协议（`NET_DVR_PlayBackByTime_V40`）从录像设备按时间区间回放录像。**搜索时不建立回放流**：返回值中的 `url` 是一个动态链接（`GET /recording-live?startTime=...&endTime=...`），播放器请求该链接时才临时建立 SDK 回放会话，并由 MCP 302 重定向到 ZLMediaKit 上的真实 FLV 地址。NVR 回放并发数受限时，逐出最早建立的会话以容纳新会话。

设备选择分两条路径：

- **传 `cameraId`（多 NVR 路径）**：先通过视频平台接口查询摄像头，随后定位其所属 NVR：
  - 摄像头 `sourceUrl`（形如 `rtsp://user:pass@<nvrIP>:554/Streaming/Channels/101`）指向已知 NVR（`HCNETSDK_HOST` 或 `HCNETSDK_DOWNLOAD_NVR_HOSTS` 中的主机）时，用内嵌账号密码对该设备做 ISAPI 录像检索（`POST /ISAPI/ContentMgmt/search`，Digest 认证）；SDK 回放通道优先取 `nvrChannel`，否则由 `nvrTrackId` 换算（如 `201`→通道 `2`）。
  - `sourceUrl` 直连 IPC 时（录像实际存储在某台 NVR 上），对 `HCNETSDK_DOWNLOAD_NVR_HOSTS` 与 `CVR_HOSTS` 中的每台设备（两者默认值均按部署网段自动选择，见环境变量表）拉取 `GET /ISAPI/ContentMgmt/InputProxy/channels` 输入代理通道列表，按源 IPC 地址反查所属 NVR 与真实通道号（平台 `nvrTrackId` 对直连 IPC 可能是批量导入的脏数据，不作准；映射整体缓存 10 分钟，凭据用 `HCNETSDK_DOWNLOAD_USERNAME`/`HCNETSDK_DOWNLOAD_PASSWORD`，CVR 用 `CVR_USERNAME`/`CVR_PASSWORD`）。反查未命中时回退按 `sourceUrl` 主机直连处理，仍未绑定 NVR（`nvrTrackId`/`nvrChannel` 均空）时报 400/ValueError。
  - 每个检索命中映射为一条录像段。设备无录像时返回空列表；设备不可达或认证失败时报错。SDK 端口默认 `8000`，可用环境变量 `HCNETSDK_DEVICE_PORT` 覆盖。
- **不传 `cameraId`（单设备路径，保持原有行为）**：`trackId` 参数会被忽略，实际回放设备与通道由 `HCNETSDK_HOST`/`HCNETSDK_PORT`/`HCNETSDK_CHANNEL` 等环境变量决定，固定返回 1 条结果。

#### 输入参数

```json
{
  "cameraId": "6f1d3f34-7ab1-4d7e-9f1e-f3d0a7b9c101",
  "startTime": "2026-06-22T09:00:00+08:00",
  "endTime": "2026-06-22T10:00:00+08:00",
  "autoProxy": true
}
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `cameraId` | `string` | 否 | 空 | 非空时按该摄像头绑定的 NVR 检索（凭据取自摄像头 `sourceUrl`）；为空时走 `HCNETSDK_*` 单设备路径。 |
| `startTime` | `string` | 是 | 无 | 查询开始时间，ISO 8601 格式；服务端按东八区北京时间归一化。 |
| `endTime` | `string` | 是 | 无 | 查询结束时间，ISO 8601 格式，必须晚于 `startTime`；服务端按东八区北京时间归一化。 |
| `limit` | `integer` | 否 | `50` | cameraId 路径为 ISAPI 检索最大条数（上限 200）；单设备路径为兼容字段，固定只返回 1 条结果。 |
| `trackId` | `string` | 否 | 空 | cameraId 路径忽略（track 取自摄像头 `nvrTrackId`）；单设备路径忽略，通道由 `HCNETSDK_CHANNEL` 决定。 |
| `autoProxy` | `boolean` | 否 | `true` | 为 `true` 时返回按需建流的动态链接（`/recording-live`）。 |
| `streamFormat` | `"flv"` | 否 | `flv` | 当前 SDK 回放仅输出 FLV。 |

#### 时间格式

推荐使用北京时间 ISO 8601。未带时区的时间也按东八区北京时间解释，避免与现场事件时间相差 8 小时：

```text
2026-06-22T09:00:00+08:00
```

也可使用未带时区的北京时间格式：

```text
2026-06-22T09:00:00
```

#### 返回值

顶层含 `input` 字段，原样回显本次调用的输入参数（`cameraId`、`startTime`、`endTime`、`limit`、`trackId`、`autoProxy`、`streamFormat`）。

```json
{
  "data": [
    {
      "recordingId": "b7d7f2e07d1e4c8d8d8c8b1c1a9a0f22",
      "cameraId": "192.168.11.198-channel-1",
      "cameraName": "IPC-192.168.11.198-1",
      "trackId": "1",
      "startTime": "2026-06-22T09:00:00+08:00",
      "endTime": "2026-06-22T10:00:00+08:00",
      "source": "hikvision_hcnetsdk_playback",
      "url": "http://192.168.11.194:8097/recording-live?startTime=2026-06-22T09%3A00%3A00%2B08%3A00&endTime=2026-06-22T10%3A00%3A00%2B08%3A00",
      "format": "flv",
      "metadata": {
        "deviceHost": "192.168.11.198",
        "devicePort": 8000,
        "channel": 1,
        "protocol": "HCNetSDK",
        "sdkApi": "NET_DVR_PlayBackByTime_V40"
      }
    }
  ],
  "xml": "<sxin-video-list count=\"1\">...</sxin-video-list>",
  "searchedTrackIds": ["1"],
  "failedTrackIds": {}
}
```

#### 安全说明

返回值不包含录像设备的原始地址凭据，也不会返回用户名或密码。`recordingId` 由设备/通道（cameraId 路径为设备/track）/时间区间确定性生成，可用于录像资源（`videoai://recordings/{recordingId}`）查询。

#### 已知限制

- 动态链接的对外基址由 `VIDEOAI_MCP_PUBLIC_BASE_URL` 决定（默认 `http://192.168.11.194:8097`），必须与客户端实际可访问的 MCP 地址一致。
- SDK 回放会话数默认不限制；仅在特定部署环境（如 NVR 回放并发受限的 demo 环境）通过 `HCNETSDK_MAX_LIVE_SESSIONS` 设置上限（如 `2`，cameraId 多 NVR 路径下每台 NVR 各建一个回放代理，各自独立计数），超出时逐出该设备最早建立的会话。新建会话失败（如 NVR 会话数/带宽限制）也会逐出最老会话后重试。回放会话有效期为 `VIDEOAI_MCP_PLAYBACK_TTL_SECONDS`（默认 1800 秒）。
- NVR 以高于实时的速度吐回调数据，而代理用 `ffmpeg -re` 实时节流；回调队列打满时会自动暂停设备供流，待队列腾出空位后恢复（背压机制，禁止丢块），不再因此导致会话失败。
- MCP 容器必须包含 `ffmpeg`，否则无法生成代理流。

### 6.3.1 `GET /recording-live`

录像回放的动态播放链接入口，由 `search_recordings` 返回的 `url` 指向该接口。请求到达时才按参数建立 HCNetSDK 回放会话，随后 `302` 重定向到 ZLMediaKit 的真实 FLV 地址；同一时段重复请求复用已存在的会话。

带 `cameraId` 时按该摄像头绑定的 NVR 建流（凭据取自摄像头 `sourceUrl`，per-device 代理按设备主机缓存复用），并通过 `/ISAPI/System/time` 测量设备时钟偏差后补偿到 SDK 回放时间；不带 `cameraId` 时使用 `HCNETSDK_*` 配置的单例设备。

该接口只提供 HTTP GET 入口，不注册为 MCP tool；与 `-http` 接口一样为匿名内网接口。

#### Query 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `cameraId` | `string` | 否 | 非空时按该摄像头绑定的 NVR 回放；为空时走 `HCNETSDK_*` 单设备路径。 |
| `startTime` | `string` | 是 | 回放开始时间，ISO 8601；未带时区按东八区北京时间解释。 |
| `endTime` | `string` | 是 | 回放结束时间，必须晚于 `startTime`。 |
| `speed` | `float` | 否 | 回放倍速，默认 `1`；仅支持 `0.25`/`0.5`/`1`/`2`/`4`/`8`/`16`/`32`，其他值报 `unsupported playback speed`。 |

#### 响应

- 成功：`302 Found`，`Location` 头指向 FLV 播放地址。
- 参数错误：`400` JSON（`{"error": {"type": "ValueError", "message": ...}}`）。
- 建流失败：`500` JSON，细节记录于 MCP 服务端日志。

### 6.3.2 `POST /get_recording_stream-http`

为 `search_recordings` 已缓存（`recordingId` 仍在 TTL 内）的录像段临时建流，返回 **H.265** 播放地址。

该接口**只提供 HTTP 兼容入口，刻意不注册为 MCP tool**——MCP tool 目录里没有 `get_recording_stream`。与 `GET /recording-live` 的区别：本接口返回 JSON（不是 302），并在 SDK 回放路径上走 **H.265 直通**。

H.265 直通把设备原码流（现场 NVR 多为 smart265/HEVC）直接封进 FLV，不做 libx264 实时转码，省去转码开销并保留设备原画质。代价是直通无法改写时间戳，因此**只支持等速**（`speed=1`），其它倍速档位返回 `400` 而不是静默降级成转码。播放端必须支持 HEVC（前端用 mpegts.js + 浏览器 HEVC MSE；flv.js 不支持 H.265）。非 SDK 源（RTSP 转发）同样走直通，因此不叠加回放水印。

#### 请求体

| 参数 | 类型 | 必填 | 默认 | 说明 |
| --- | --- | --- | --- | --- |
| `recordingId` | `string` | 是 | — | `search_recordings` 返回并缓存过的录像段 ID。 |
| `format` | `string` | 否 | `flv` | 非 SDK 源的输出容器，可选 `flv` 或 `hls`；SDK 源固定 `flv`。 |
| `speed` | `float` | 否 | `1` | 回放倍速；H.265 直通仅支持 `1`。 |

#### 响应

成功返回 `200` JSON：

```json
{
  "url": "http://192.168.11.194:81/live/hcn-h265-<recordingId>.live.flv",
  "format": "flv",
  "expiresAt": "2026-06-22T10:00:00+00:00",
  "source": "hikvision_hcnetsdk_playback",
  "metadata": {
    "cameraId": "6f1d3f34-7ab1-4d7e-9f1e-f3d0a7b9c101",
    "cameraName": "金山12楼门口",
    "recordingId": "rec-...",
    "trackId": "601",
    "startTime": "2026-06-22T09:00:00+08:00",
    "endTime": "2026-06-22T10:00:00+08:00",
    "codec": "h265"
  },
  "xml": "<sxin-video-file url=\"...\" format=\"flv\" source=\"...\" codec=\"h265\" .../>",
  "input": {"recordingId": "rec-...", "format": "flv", "speed": 1.0, "codec": "h265"}
}
```

错误响应与其它 `-http` 接口一致（`400` JSON / `500` JSON）：

- `recordingId` 未知或已过期：`400`，消息 `recordingId is unknown or expired; call search_recordings again`。
- H.265 直通配非等速：`400`，消息 `codec h265 passes the device bitstream through and only supports speed 1.0`。

### 6.4 `download_recording`

使用 HCNetSDK `NET_DVR_GetFileByTime` 从指定设备下载指定时间范围录像，remux 为 MP4 并保存到 MinIO。下载前会通过 `/ISAPI/System/time` 自动测量设备时钟偏差并补偿（SDK 时间按设备本地时钟解释）。

设备选择分两条路径：传 `cameraId` 时按该摄像头所属的 NVR 下载（设备定位方式与 `search_recordings` 的 cameraId 路径一致：sourceUrl 指向已知 NVR 时用内嵌凭据，直连 IPC 时经 `HCNETSDK_DOWNLOAD_NVR_HOSTS` 反查所属 NVR 与真实通道，不受 `nvr` 白名单限制）；否则使用 `nvr` 白名单路径。两者都为空时按 `nvr` 校验报错。

#### 输入参数

```json
{
  "nvr": "10.10.7.252",
  "startTime": "2026-07-14T11:22:10+08:00",
  "endTime": "2026-07-14T11:23:10+08:00",
  "trackId": "201",
  "speedx": 16
}
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `nvr` | `string` | 是 | 无 | NVR 名称/IP，只接受 `HCNETSDK_DOWNLOAD_NVR_HOSTS` 配置的主机（默认 `10.10.7.252,10.10.7.253`）；传 `cameraId` 时忽略，可填空字符串。 |
| `cameraId` | `string` | 否 | 空 | 非空时按该摄像头绑定的 NVR 下载（凭据取自摄像头 `sourceUrl`），优先于 `nvr`/`channel`/`trackId`。 |
| `startTime` | `string` | 是 | 无 | 下载开始时间，ISO 8601 格式；无时区时按北京时间解释。 |
| `endTime` | `string` | 是 | 无 | 下载结束时间，必须晚于 `startTime`；无时区时按北京时间解释。 |
| `trackId` | `string` | 否 | 空 | 海康 track ID（如 `201`），自动换算 SDK 通道号（`201`→通道 `2`）。 |
| `channel` | `int` | 否 | `0` | 显式 SDK 通道号，优先级高于 `trackId`；都为 0/空时用 `HCNETSDK_DOWNLOAD_CHANNEL`。 |
| `speedx` | `int` | 否 | `1` | NVR 侧下载流控倍速，可选值 `1/2/4/8/16/32`，映射 HCNetSDK `NET_DVR_SETSPEED` 的流控值（单位 Mbps，范围 0~32）。`1` 为默认值，不下发流控命令，按设备默认速度下载；设备不支持设速时记录告警并按默认速度继续（只影响下载耗时，不影响文件内容）。 |

下载账号：白名单路径由 `HCNETSDK_DOWNLOAD_USERNAME`/`HCNETSDK_DOWNLOAD_PASSWORD` 配置；cameraId 路径取摄像头 `sourceUrl` 内嵌凭据。账号需具备回放/下载权限，否则 SDK 会报 `NET_DVR_PlayBackControl download start failed: 17`（无权限）。

#### 返回值

返回结构与 `search_recordings` 一致（含 `data`、`xml`、`searchedTrackIds`、`failedTrackIds`），`data[0].url` 为 MinIO 中的 MP4 文件地址。

```json
{
  "data": [
    {
      "recordingId": "d80db5119f34d144333d0c21630dbf6f",
      "cameraId": "10.10.7.252-channel-1",
      "cameraName": "IPC-10.10.7.252-1",
      "trackId": "1",
      "startTime": "2026-07-14T11:22:10+08:00",
      "endTime": "2026-07-14T11:23:10+08:00",
      "source": "hikvision_hcnetsdk_download",
      "url": "http://192.168.11.194:9000/public/recordings/10.10.7.252/ch1/d80db5119f34d144333d0c21630dbf6f.mp4",
      "format": "mp4",
      "metadata": {
        "deviceHost": "10.10.7.252",
        "devicePort": 8000,
        "channel": 1,
        "protocol": "HCNetSDK",
        "sdkApi": "NET_DVR_GetFileByTime",
        "objectName": "recordings/10.10.7.252/ch1/d80db5119f34d144333d0c21630dbf6f.mp4"
      }
    }
  ],
  "xml": "<sxin-video-list count=\"1\">...</sxin-video-list>",
  "searchedTrackIds": ["1"],
  "failedTrackIds": {}
}
```

### 6.5 `export_recording`

通过 HCNetSDK 按时间下载（`NET_DVR_GetFileByTime`）把指定时间范围的录像导出为 MP4 并上传 MinIO，返回可直接 HTTP 访问的文件地址。供"文搜视频"等需要视频文件 URL 的场景使用。

实测约束（远程 NVR 192.168.11.251）：

- 导出优先走 HCNetSDK 按时间下载：非实时抓流，墙钟耗时取决于网络带宽，远快于录像时长。传入 `cameraId` 时按该摄像头所属的 NVR 下载（设备定位方式与 `search_recordings` 的 cameraId 路径一致：sourceUrl 指向已知 NVR 时用内嵌凭据，直连 IPC 时经 `HCNETSDK_DOWNLOAD_NVR_HOSTS` 反查所属 NVR 与真实通道）；不传时按 `trackId` 对白名单 NVR（`HIKVISION_NVR_BASE_URL` 主机）下载。SDK 下载不可用或失败时，20 分钟以内的时段回退 RTSP 回放抓流（`/Streaming/tracks/{trackId}/?starttime=...&endtime=...`，吐流约 1x 速度，导出墙钟耗时 ≈ 所选时长；仅无 `cameraId` 的白名单路径支持该兜底）。单次导出总上限 7200 秒（2 小时）。
- `starttime`/`endtime` 的 `Z` 后缀数字（RTSP 路径）与 SDK 下载时间均按 **NVR 本地时钟**解释；NVR 为手动对时，接口会先请求 `/ISAPI/System/time` 测量 NVR 与服务器时钟偏差并自动补偿。
- RTSP 兜底路径下 NVR 不遵守 `endtime`，导出由 ffmpeg `-t` 按时长截断。

#### 输入参数

```json
{
  "trackId": "201",
  "startTime": "2026-08-31T10:00:00+08:00",
  "endTime": "2026-08-31T10:02:00+08:00"
}
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `trackId` | `string` | 否 | `601` | NVR 回放 track（如 `201`，对应摄像头 `nvrTrackId`）。传 `cameraId` 时忽略。 |
| `cameraId` | `string` | 否 | 无 | 平台摄像头 ID；传入后按该摄像头 `sourceUrl` 内嵌凭据连接其绑定的 NVR/设备下载，通道号取 `nvrChannel` 或由 `nvrTrackId` 换算。 |
| `startTime` | `string` | 是 | 无 | 开始时间，ISO 8601；无时区时按北京时间解释。 |
| `endTime` | `string` | 是 | 无 | 结束时间，必须晚于 `startTime`；跨度不超过 7200 秒。 |

#### 返回值

```json
{
  "data": {
    "videoUrl": "http://192.168.11.194:9000/public/recordings/exports/201/<uuid>.mp4",
    "durationSeconds": 120,
    "trackId": "201",
    "startTime": "2026-08-31T10:00:00+08:00",
    "endTime": "2026-08-31T10:02:00+08:00",
    "nvrClockSkewSeconds": -56400,
    "exportElapsedSeconds": 122.5
  }
}
```

`nvrClockSkewSeconds` 为导出时测得的 NVR 时钟偏差（NVR 时间减服务器时间，秒），用于排查时间对不上问题。该时段无有效录像时返回错误。SDK 按时间下载路径（含 cameraId 路径与白名单 SDK 路径）返回额外包含 `exportMethod: "hcnetsdk_download"` 字段；RTSP 兜底路径无此字段。

### 6.6 `video_understanding`

代理调用视频理解结果结构化展示服务（`VIDEO_UNDERSTANDING_API_BASE_URL`，默认 `http://10.10.3.100:8780` 的 `POST /api/v1/video-understanding/structure`）：上游先对 MP4 视频做理解分析，再用 DeepSeek 将结果整理为结构化事件（事件名称、时间范围、简要描述、与用户问题的相关性评分），按事件时间范围截取关键帧，并选出与问题最相关的重点事件。响应原样透传（`code`/`message`/`data`，`data` 含 `summary`、`answer_status`、`focus_event`、`events`、`raw_understanding_result` 等字段）。理解 + 结构化 + 截帧耗时较长，默认超时 600 秒（`VIDEO_UNDERSTANDING_TIMEOUT_SECONDS`）。

#### 输入参数

```json
{
  "videoUrl": "http://192.168.11.194:9000/public/xxx.mp4",
  "question": "视频中是否发生了人员跌倒？",
  "fps": 1,
  "segmentSeconds": 60,
  "maxSegments": 0,
  "height": 480,
  "prompt": "请分析视频中的主要人员、物体、行为及异常事件"
}
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `videoUrl` | `string` | 是 | 无 | MP4 视频文件 URL（如 MinIO 地址，可由 `export_recording` 生成）；上游理解与关键帧截取均使用该地址。 |
| `question` | `string` | 是 | 无 | 用户问题，用于判断理解结果能否回答问题并选出重点事件。 |
| `fps` | `int` | 否 | `1` | 上游抽帧频率，小于 1 按 1 处理。 |
| `segmentSeconds` | `int` | 否 | `60` | 上游长视频切片时长（秒），小于 1 按 1 处理。 |
| `maxSegments` | `int` | 否 | `0` | 上游最大分析片段数，`0` 表示全部分析，负数按 0 处理。 |
| `height` | `int` | 否 | `480` | 上游视频压缩高度，小于 1 按 1 处理。 |
| `prompt` | `string` | 否 | `请分析视频中的主要人员、物体、行为及异常事件` | 发送给上游视频理解接口的提示词，留空用默认值。 |

#### 返回值

透传上游响应（结构节选，完整字段见《视频理解接口》文档）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "question": "这个视频里是否有人坐下？",
    "summary": "视频显示在室内楼梯平台上，绿衣女子几乎全程坐在台阶上休息……",
    "answer_status": "found",
    "focus_event": {
      "event_id": "event_001",
      "event_name": "绿衣女子坐在台阶上休息",
      "time_range": { "start_seconds": 0.0, "end_seconds": 29.0, "display_text": "0-29秒" },
      "description": "绿衣女子在整个视频中坐在楼梯平台的台阶上……",
      "relevance_score": 10.0,
      "is_focus": true,
      "key_frame": {
        "image_path": "2026-09-10/20260910-163703_875173fdfcdd_1a91e0cf/event_001_14.50s_focus_39c71810.jpg",
        "image_url": "http://192.168.11.194:29000/video-keyframes/2026-09-10/20260910-163703_875173fdfcdd_1a91e0cf/event_001_14.50s_focus_39c71810.jpg",
        "image_base64": null,
        "mime_type": "image/jpeg",
        "timestamp_seconds": 14.5,
        "extraction_status": "success",
        "error_message": null
      }
    },
    "events": [],
    "raw_understanding_result": {}
  }
}
```

`answer_status` 取值：`found`（可回答）/ `not_found`（无法回答，此时 `focus_event` 为 `null`、`events` 为空数组）/ `uncertain`（不确定）。上游校验或调用失败时按统一错误格式透传（如 `VALIDATION_001`、`UPSTREAM_001`、`LLM_001`、`VIDEO_001`）。

### 6.7 `upload_face_image`

通过图片 URL 上传人脸照片到人脸库，并按传入参数创建一个默认开启的人脸布控任务。MCP Server 会下载图片 URL 的内容，并转发给后端人脸库接口；人脸库当前只保留一张照片，新上传会覆盖旧照片。创建的布控任务会出现在布控任务页面，默认 `enabled=true`、`taskStatus=running`。

#### 输入参数

```json
{
  "imageUrl": "http://192.168.11.194:9000/public/faces/person.jpg",
  "cameraId": "cam-1",
  "modelName": "retinaface_mobilenet",
  "name": "张三"
}
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `imageUrl` | `string` | 是 | 无 | 图片 URL，必须可由 MCP Server 访问。 |
| `cameraId` | `string` | 是 | 无 | 摄像头 ID，布控任务会绑定到该摄像头。 |
| `modelName` | `string` | 是 | 无 | 算法模型名称，作为布控任务流程名。 |
| `name` | `string` | 否 | `人脸库照片` | 人脸名称，同时作为布控任务名称。 |

#### 返回值

```json
{
  "faceId": "5e0a5730-a07e-4404-9774-a75621642542",
  "face": {
    "id": "5e0a5730-a07e-4404-9774-a75621642542",
    "name": "张三",
    "photoUrl": "/api/assets/faces/5e0a5730-a07e-4404-9774-a75621642542.jpg"
  },
  "deploymentTaskId": "6f3d3c25-3d75-4c28-bd4f-0c7184f5487b",
  "deploymentTask": {
    "id": "6f3d3c25-3d75-4c28-bd4f-0c7184f5487b",
    "name": "张三",
    "pipeline": "retinaface_mobilenet",
    "enabled": true,
    "taskStatus": "running",
    "faceProfileId": "5e0a5730-a07e-4404-9774-a75621642542",
    "cameraIds": ["cam-1"]
  }
}
```

### 6.8 文搜图 / 图搜图 tools

以下 tools 对应前端"文搜图""图搜图"页面使用的接口。

| Tool | 输入 | 上游接口 |
| --- | --- | --- |
| `text_search_images` | `{"message":"穿红衣服的人","startTime":"2026-08-31 09:00","endTime":"2026-08-31 10:00","location":"园区南门","page":1,"pageSize":10}` | `POST {RETRIEVE_API_BASE_URL}/v1/retrieve/query` |
| `search_person_by_image` | `{"imageUrl":"http://.../query.jpg","bbox":[{"x":550,"y":198}],"searchMethod":"reid","startTime":"2024-12-12 07:51:15","endTime":"2026-12-12 08:50:17","similarityThreshold":0.6,"topK":10,"waitTimeoutSeconds":120}` | 组合调用 detectPersons → searchPersonByBbox → searchPersonResult |

`text_search_images`（文搜图）：按自然语言描述检索人员/车辆图片，`message` 必填；`startTime`/`endTime`/`location` 可空；`pageSize` 上限 100。返回值透传检索服务响应（`data.items` 为命中图片及属性）。

`search_person_by_image`（图搜图）：一站式以图搜人。未传 `bbox` 时先调用 `detect_persons` 取第一个人形框；随后提交搜索任务并每 2 秒轮询，直到任务成功（返回含 `similar_persons` 的最终结果）或失败/超时（`waitTimeoutSeconds` 默认 120 秒）。已传 `bbox` 时跳过检测直接提交。`startTime`/`endTime` 可选，透传给上游 `searchPersonByBbox` 限定检索时间范围；提交任务失败时报 `搜索任务提交失败`。

### 6.9 图搜人和步态识别 tools

以下 tools 封装 `PERSON_API_BASE_URL` 指向的人员检索服务，默认上游为 `http://192.168.11.192:18890`。返回值透传上游 JSON；上游 4xx 业务响应会额外包含 `upstreamStatusCode` 字段。

| Tool | 输入 | 上游接口 |
| --- | --- | --- |
| `detect_persons` | `{"imageUrl":"http://.../query.jpg"}` | `POST /vlm-application/search/detectPersons` |
| `search_person_by_bbox` | `{"imageUrl":"http://.../query.jpg","bbox":[{"x":550,"y":198},{"x":786,"y":198},{"x":786,"y":667},{"x":550,"y":667}],"searchMethod":"reid","startTime":"2024-12-12 07:51:15","endTime":"2026-12-12 08:50:17","similarityThreshold":0.6,"topK":10}` | `POST /vlm-application/search/searchPersonByBbox` |
| `get_person_search_result` | `{"taskId":"550e8400-e29b-41d4-a716-446655440000"}` | `GET /vlm-application/search/searchPersonResult/{task_id}` |
| `detect_persons_with_id` | `{"imageUrl":"http://.../query.jpg"}` | `POST /vlm-application/search/detectPersonsWithId` |
| `get_person_bbox` | `{"personId":"a1b2c3d4-e5f6-7890-abcd-ef1234567890"}` | `GET /vlm-application/search/getPersonBbox/{person_id}` |
| `gait_feature_compare` | `{"persons":[{"id":"person_001","isWalking":true},{"id":"person_002","isWalking":true}]}` | `POST /vlm-application/gait/gaitFeaCompare` |

`search_person_by_bbox` 会把 MCP 参数转换为上游字段名：`imageUrl` -> `image_url`、`searchMethod` -> `search_method`、`startTime` -> `start_time`、`endTime` -> `end_time`、`similarityThreshold` -> `similarity_threshold`、`topK` -> `top_k`。

### 6.10 `query_face_matches`

查询人脸库抓拍匹配事件，按视频时间倒序。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `faceId` | `string` | 否 | 空 | 指定人脸 ID 时只返回该人脸的匹配事件；为空时返回全部人脸的最新事件。 |
| `limit` | `int` | 否 | `10` | 返回条数上限，最大 10，超出按 10 处理。 |

返回 `{"data": [...], "count": N}`，`data` 为匹配事件数组。

### 6.11 `dino_events`

返回 DINO 物品识别事件（当前为演示用 mock 数据：事件图片为生成的 SVG 占位图，事件点位取自摄像头列表，事件描述取自名称含 "dino" 的布控任务）。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `limit` | `int` | 否 | `10` | 返回条数，上限 10。 |

返回 `{"data": [...], "count": N, "xml": "..."}`，`data` 为事件数组（`eventId`/`eventSource`/`eventType`/`eventLocation`/`occurredAt`/`eventImage`/`eventDescription` 等字段）。

## 7. Resources

### 7.1 `videoai://cameras/{cameraId}`

读取单个摄像头资源。

示例：

```text
videoai://cameras/6f1d3f34-7ab1-4d7e-9f1e-f3d0a7b9c101
```

返回 VideoAI 后端摄像头完整对象，包含直播 URL、状态、NVR 绑定字段等。

### 7.2 `videoai://recordings/{recordingId}`

读取缓存中的历史录像片段资源。

示例：

```text
videoai://recordings/b7d7f2e07d1e4c8d8d8c8b1c1a9a0f22
```

返回历史录像片段元数据，不包含 NVR 原始 `playbackURI`。

## 8. 错误说明

| 场景 | 典型错误 |
| --- | --- |
| `cameraId` 不存在 | VideoAI Backend 返回 404。 |
| `endTime <= startTime` | `endTime must be later than startTime`。 |
| 未配置 `HIKVISION_NVR_BASE_URL` | `HIKVISION_NVR_BASE_URL is not configured`。 |
| 未配置 NVR 用户名或密码 | `Hikvision NVR credentials are not configured`。 |
| 摄像头未绑定 `nvrTrackId` 或 `nvrChannel` | `camera {cameraId} is not bound to an NVR: nvrTrackId/nvrChannel is missing`。 |
| `recordingId` 不存在或过期 | `recordingId is unknown or expired; call search_recordings again`。 |
| FFmpeg/ZLMediaKit 转推失败 | 返回的播放 URL 不可用，需要检查 MCP 日志和 ZLMediaKit 流列表。 |
| SDK 回放会话失败 | `HCNetSDK playback failed`（附具体会话/ffmpeg 错误细节），重试即可；回调队列打满时已改为背压暂停供流，不再报错。 |
| 录像回放倍速不支持 | `unsupported playback speed: {speed}; supported: ...`，改用支持的档位（0.25/0.5/1/2/4/8/16/32）。 |
| `export_recording` 时段无录像 | `该时段无可用录像`。 |
| `export_recording` 跨度超限 | `export duration must not exceed 7200 seconds`。 |
| `export_recording` 抓流停滞超时 | 自动用已抓到的部分出片；内容不足时报 `该时段无可用录像`。 |
| `text_search_images` 描述为空 | `message is required`。 |
| `search_person_by_image` 图片中无人 | `未检测到人，请重新上传`。 |
| `search_person_by_image` 任务提交失败 | `搜索任务提交失败`。 |
| `search_person_by_image` 任务失败/超时 | `搜索任务失败` / `搜索任务超时，请稍后重试`。 |
| 上游 4xx 业务响应 | 响应体包含 `upstreamStatusCode` 字段（人员检索/文搜图/视频分析类 tools）。 |

## 9. 调用流程建议

### 实时视频

1. 调用 `list_cameras` 获取摄像头列表。
2. 选择 `cameraId`。
3. 调用 `get_live_stream`。
4. 客户端使用返回的 `url` 播放视频。

### 历史录像

1. 调用 `search_recordings`，传入需要回放的时间范围；传 `cameraId` 时按该摄像头绑定的 NVR 检索回放（多 NVR），不传时回放设备/通道由服务端 `HCNETSDK_*` 配置决定。
2. 从返回的 `data` 中取 `url`（`/recording-live` 动态链接）直接交给播放器；链接在首次请求时才建立回放流，NVR 会话数受限时会逐出最老会话。需要倍速时在链接后追加 `&speed=`（如 `&speed=8`）。
3. 客户端跟随 302 后播放 `.flv` 视频。

### 文搜视频（录像内容分析）

1. 调用 `list_cameras`（可按 `name` 过滤、用 `page`/`pageSize` 翻页），取目标摄像头的 `id` 作为 `cameraId`。
2. 调用 `export_recording`，传入 `cameraId`（或 `trackId`）和时间段，等待导出（默认走 HCNetSDK 按时间下载，非实时、更快；SDK 不可用时 20 分钟内的白名单 trackId 时段回退 RTSP 抓流，耗时 ≈ 所选时长），得到 MinIO MP4 `videoUrl`。
3. 调用 `video_understanding`，传入 `videoUrl` 和中文 `question`（用户问题），读取结构化事件、重点事件与关键帧。

### 文搜图

1. 调用 `text_search_images`，`message` 传入中文描述（如"穿红衣服的人"），可选时间/地点过滤。
2. 从返回的 `data.items` 读取命中图片地址与属性。

### 图搜图（以图搜人）

1. 准备一张可内网访问的图片 URL（如 MinIO 地址）。
2. 调用 `search_person_by_image` 一站式完成检测、提交与轮询，直接读取结果中的 `similar_persons`。
3. 需要分步控制时，可依次调用 `detect_persons` → `search_person_by_bbox` → `get_person_search_result`。

### 人脸布控

1. 调用人脸图片 URL 可用的 `upload_face_image`，上传人脸照片并自动创建布控任务。
2. 调用 `query_face_matches` 查询抓拍匹配记录。

## 10. 部署示例

`.env` 示例：

```bash
VIDEOAI_MCP_PLAYBACK_TTL_SECONDS=1800
PERSON_API_BASE_URL=http://192.168.11.192:18890
RETRIEVE_API_BASE_URL=http://192.168.11.194:15011
RETRIEVE_API_TIMEOUT_SECONDS=120
VIDEO_UNDERSTANDING_API_BASE_URL=http://10.10.3.100:8780
VIDEO_UNDERSTANDING_TIMEOUT_SECONDS=600
HIKVISION_NVR_BASE_URL=http://192.168.1.64
HIKVISION_NVR_USERNAME=admin
HIKVISION_NVR_PASSWORD=change-me
HCNETSDK_HOST=192.168.11.198
HCNETSDK_PORT=8000
HCNETSDK_USERNAME=admin
HCNETSDK_PASSWORD=cisdi123
HCNETSDK_CHANNEL=1
HCNETSDK_MAX_LIVE_SESSIONS=0
HCNETSDK_DOWNLOAD_NVR_HOSTS=
HCNETSDK_DOWNLOAD_PORT=8000
HCNETSDK_DOWNLOAD_USERNAME=admin
HCNETSDK_DOWNLOAD_PASSWORD=change-me
HCNETSDK_DOWNLOAD_CHANNEL=1
# 置空时按部署网段自动选择（10 网段 → NVR 10.10.7.252/253；172 网段 → CVR 172.21.200.21/22/23）
CVR_HOSTS=
MINIO_ENDPOINT=192.168.11.194
MINIO_PORT=9000
MINIO_USE_SSL=false
MINIO_ACCESS_KEY=minio
MINIO_SECRET_KEY=Klg4dM9F3H
MINIO_BUCKET=public
```

启动：

```bash
docker compose up --build -d backend zlm mcp-server
```

MCP 客户端连接：

```text
http://192.168.11.194:8097/mcp
```
