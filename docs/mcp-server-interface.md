# VideoAI MCP Server 接口说明书

## 1. 概述

VideoAI MCP Server 用于向 MCP 客户端暴露视频监控能力：

- 查询 VideoAI 摄像头列表。
- 获取指定摄像头实时视频播放地址。
- 查询海康 NVR 历史录像。
- 获取历史录像短期 FLV/HLS 播放地址，默认 FLV。

视频字节流不通过 MCP 协议传输。MCP tools 只返回播放 URL，实际播放由 HTTP/ZLMediaKit 等媒体服务完成。

## 2. 服务信息

默认服务名：

```text
videoai-monitoring
```

默认 MCP 入口：

```text
http://192.168.11.194:8097/mcp
```

同一服务内还提供匿名 HTTP JSON 入口，路径为 `/<mcp接口>-http`。HTTP 接口使用 `POST`，请求体为 JSON object，功能和同名 MCP tool 一致。

```text
http://192.168.11.194:8097/list_cameras-http
http://192.168.11.194:8097/get_live_stream-http
http://192.168.11.194:8097/search_recordings-http
http://192.168.11.194:8097/get_recording_stream-http
http://192.168.11.194:8097/download_recording-http
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

- VideoAI Backend：读取摄像头列表、获取摄像头详情、启动直播。
- Person API：封装 `192.168.11.192:18890` 的图搜人和步态识别接口。
- ZLMediaKit：把海康回放码流转为 FLV/HLS 播放地址。
- MinIO：保存 `download_recording` 生成的 MP4 文件。

## 4. 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `VIDEOAI_BACKEND_URL` | `http://localhost:8081` | VideoAI 后端地址。Docker Compose 中默认为 `http://backend:8081`。 |
| `PERSON_API_BASE_URL` | `http://192.168.11.192:18890` | 图搜人和步态识别上游服务地址。 |
| `VIDEOAI_ZLM_HTTP_URL` | `http://localhost:8080` | ZLMediaKit 内部 API 地址。 |
| `VIDEOAI_ZLM_PUBLIC_HTTP_URL` | 同 `VIDEOAI_ZLM_HTTP_URL` | 返回给客户端的播放地址前缀，应配置为客户端所在网络可访问的 ZLMediaKit HTTP 地址。 |
| `VIDEOAI_ZLM_SECRET` | 项目默认 secret | ZLMediaKit API secret。 |
| `VIDEOAI_ZLM_RTMP_PUSH_BASE` | `rtmp://localhost/live` | 转推历史回放流的 RTMP 目标前缀。 |
| `HIKVISION_NVR_BASE_URL` | 空 | 海康 NVR 地址，例如 `http://192.168.1.64`。 |
| `HIKVISION_NVR_USERNAME` | 空 | 海康 NVR 用户名。 |
| `HIKVISION_NVR_PASSWORD` | 空 | 海康 NVR 密码。 |
| `HCNETSDK_HOST` | `192.168.11.198` | HCNetSDK 私有协议录像设备地址。 |
| `HCNETSDK_PORT` | `8000` | HCNetSDK 私有协议端口。 |
| `HCNETSDK_USERNAME` | `admin` | HCNetSDK 登录用户名。 |
| `HCNETSDK_PASSWORD` | `cisdi123` | HCNetSDK 登录密码。 |
| `HCNETSDK_CHANNEL` | `1` | 默认录像通道。 |
| `HCNETSDK_DOWNLOAD_NVR_HOSTS` | `10.10.7.252,10.10.7.253` | `download_recording` 允许选择的 NVR 名称/IP，使用逗号分隔。 |
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

## 5. 摄像头 NVR 绑定字段

历史录像查询依赖摄像头上的 NVR 绑定信息。摄像头对象新增以下可选字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `nvrId` | `string|null` | NVR 标识，用于区分设备或做展示。 |
| `nvrChannel` | `string|null` | NVR 通道号。未配置 `nvrTrackId` 时可作为查询 track ID 使用。 |
| `nvrTrackId` | `string|null` | 海康 NVR 回放 track ID，优先级高于 `nvrChannel`。 |
| `nvrStreamType` | `string|null` | 码流类型，例如 `main`、`sub`，当前主要用于元数据返回。 |

当前客户演示环境查询 NVR `192.168.11.251` 的录像。调用 `search_recordings` 时可通过 `trackId` 指定通道；未指定时默认使用通道 `601`。该接口固定只返回 1 条结果。

## 6. Tools

以下 MCP tools 均有对应 HTTP JSON 接口，接口名为 `/<tool名称>-http`，例如 `search_recordings` 对应 `/search_recordings-http`。HTTP 成功响应直接返回同名 MCP tool 的 JSON 结果；参数错误返回 `400` JSON，服务端异常返回 `500` JSON。

### 6.1 `list_cameras`

查询 VideoAI 后端中配置的摄像头列表。

#### 输入参数

无。

#### 返回值

返回摄像头数组。

```json
[
  {
    "cameraId": "6f1d3f34-7ab1-4d7e-9f1e-f3d0a7b9c101",
    "name": "Gate Camera",
    "status": "RUNNING",
    "url": "http://localhost:8081/api/streams/live/camera1.mjpeg",
    "livePlaybackUrl": "http://localhost:8081/api/streams/live/camera1.mjpeg",
    "sourceUrl": "rtsp://192.168.1.20/Streaming/Channels/101",
    "nvrBinding": {
      "bound": true,
      "nvrId": "main-nvr",
      "nvrChannel": "1",
      "nvrTrackId": "101",
      "nvrStreamType": "main"
    }
  }
]
```

#### 字段说明

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `cameraId` | `string` | 摄像头 ID。 |
| `name` | `string` | 摄像头名称。 |
| `status` | `string` | 摄像头状态，例如 `RUNNING`、`STOPPED`。 |
| `url` | `string` | 实时流播放地址。 |
| `livePlaybackUrl` | `string` | 兼容旧客户端的实时流播放地址，值与 `url` 一致。 |
| `sourceUrl` | `string` | 摄像头原始源地址。 |
| `nvrBinding.bound` | `boolean` | 是否具备 NVR 历史录像查询绑定。 |
| `nvrBinding.nvrId` | `string|null` | NVR 标识。 |
| `nvrBinding.nvrChannel` | `string|null` | NVR 通道。 |
| `nvrBinding.nvrTrackId` | `string|null` | 海康 track ID。 |
| `nvrBinding.nvrStreamType` | `string|null` | 码流类型。 |

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

```json
{
  "url": "http://localhost:8081/api/streams/live/camera1.mjpeg",
  "format": "mjpeg",
  "expiresAt": null,
  "source": "live",
  "metadata": {
    "cameraId": "6f1d3f34-7ab1-4d7e-9f1e-f3d0a7b9c101",
    "cameraName": "Gate Camera",
    "status": "RUNNING",
    "streamApp": "live",
    "streamName": "camera1"
  }
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

按时间区间构造海康 NVR RTSP 回放流，并返回可选的 ZLMediaKit 代理播放地址。

#### 输入参数

```json
{
  "cameraId": "6f1d3f34-7ab1-4d7e-9f1e-f3d0a7b9c101",
  "startTime": "2026-06-22T09:00:00+08:00",
  "endTime": "2026-06-22T10:00:00+08:00",
  "limit": 1,
  "autoProxy": true,
  "streamFormat": "flv"
}
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `cameraId` | `string` | 否 | 空 | 演示模式下会被忽略，不决定 NVR 或查询通道。 |
| `startTime` | `string` | 是 | 无 | 查询开始时间，ISO 8601 格式；服务端按东八区北京时间归一化。 |
| `endTime` | `string` | 是 | 无 | 查询结束时间，ISO 8601 格式，必须晚于 `startTime`；服务端按东八区北京时间归一化。 |
| `limit` | `integer` | 否 | `1` | 兼容字段，当前固定只返回 1 条结果。 |
| `trackId` | `string` | 否 | `601` | 可指定一个或多个通道，支持逗号分隔；只使用第一个通道；为空时默认 `601`。 |
| `autoProxy` | `boolean` | 否 | `true` | 为 `true` 时先关闭已有历史流，再为当前录像建立代理流，保证同时只有一路录像流工作。 |
| `streamFormat` | `"flv"`/`"hls"` | 否 | `flv` | 返回的代理流格式。 |

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

```json
[
  {
    "recordingId": "b7d7f2e07d1e4c8d8d8c8b1c1a9a0f22",
    "cameraId": "192.168.11.251-track-601",
    "cameraName": "NVR-192.168.11.251-601",
    "trackId": "601",
    "startTime": "2026-06-22T09:00:00+08:00",
    "endTime": "2026-06-22T09:10:00+08:00",
    "source": "hikvision_rtsp_direct",
    "url": "http://192.168.11.194:81/live/rec-b7d7f2e07d1.live.flv",
    "format": "flv",
    "metadata": {
      "nvrId": "192.168.11.251",
      "nvrChannel": "601",
      "nvrStreamType": "main"
    }
  }
]
```

#### 安全说明

返回值不包含海康 NVR 的原始 RTSP 地址，也不会返回用户名或密码。`recordingId` 是服务端生成的短期缓存 ID，用于后续调用 `get_recording_stream`。

当 NVR 回放 RTSP 返回 `453 Not Enough Bandwidth` 时，服务端会使用已挂载的演示录像文件生成同格式代理流，仍通过 `url` 返回 FLV/HLS 地址。MCP 容器必须包含 `ffmpeg`，否则无法生成代理流。

### 6.4 `get_recording_stream`

获取某个历史录像片段的短期 FLV/HLS 播放地址，默认 FLV。

#### 输入参数

```json
{
  "recordingId": "b7d7f2e07d1e4c8d8d8c8b1c1a9a0f22",
  "format": "flv"
}
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `recordingId` | `string` | 是 | 无 | `search_recordings` 返回的录像 ID。 |
| `format` | `"flv"`/`"hls"` | 否 | `flv` | 播放地址格式。 |

#### 返回值

```json
{
  "url": "http://localhost:8080/live/rec-b7d7f2e07d1.live.flv",
  "format": "flv",
  "expiresAt": "2026-06-22T02:05:00+00:00",
  "source": "hikvision_rtsp_direct",
  "metadata": {
    "nvrId": "192.168.11.251",
    "nvrChannel": "601",
    "nvrStreamType": "main",
    "cameraId": "192.168.11.251-track-601",
    "cameraName": "NVR-192.168.11.251-601",
    "recordingId": "b7d7f2e07d1e4c8d8d8c8b1c1a9a0f22",
    "trackId": "601",
    "startTime": "2026-06-22T01:00:00+00:00",
    "endTime": "2026-06-22T01:10:00+00:00"
  }
}
```

#### 行为说明

- `recordingId` 必须来自同一 MCP Server 实例近期的 `search_recordings` 结果。
- 默认缓存有效期为 `VIDEOAI_MCP_PLAYBACK_TTL_SECONDS`，默认 `1800` 秒。
- 如果缓存过期，需要重新调用 `search_recordings`。
- 调用时会通过 FFmpeg/ZLMediaKit 把 NVR 回放地址转推为 FLV/HLS。

### 6.5 `download_recording`

使用 HCNetSDK `NET_DVR_GetFileByTime` 从 `nvr` 指定的设备下载指定时间范围录像，remux 为 MP4 并保存到 MinIO。当前允许选择 `10.10.7.252` 或 `10.10.7.253`，端口为 `8000`、通道为 `1`。

#### 输入参数

```json
{
  "nvr": "10.10.7.252",
  "startTime": "2026-07-14T11:22:10+08:00",
  "endTime": "2026-07-14T11:23:10+08:00"
}
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `nvr` | `string` | 是 | 无 | NVR 名称/IP，只接受 `10.10.7.252` 或 `10.10.7.253`。 |
| `startTime` | `string` | 是 | 无 | 下载开始时间，ISO 8601 格式；无时区时按北京时间解释。 |
| `endTime` | `string` | 是 | 无 | 下载结束时间，必须晚于 `startTime`；无时区时按北京时间解释。 |

#### 返回值

返回结构与 `search_recordings` 一致，`data[0].url` 为 MinIO 中的 MP4 文件地址。

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
  "searchedTrackIds": ["1"],
  "failedTrackIds": {}
}
```

### 6.6 `upload_face_image`

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

### 6.7 图搜人和步态识别 tools

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
| `endTime <= startTime` | `endTime must be after startTime`。 |
| 未配置 `HIKVISION_NVR_BASE_URL` | `HIKVISION_NVR_BASE_URL is not configured`。 |
| 未配置 NVR 用户名或密码 | `Hikvision NVR credentials are not configured`。 |
| 摄像头未绑定 `nvrTrackId` 或 `nvrChannel` | `Camera {cameraId} is not bound to a Hikvision track/channel`。 |
| `recordingId` 不存在或过期 | `recordingId is unknown or expired; call search_recordings again`。 |
| FFmpeg/ZLMediaKit 转推失败 | 返回的播放 URL 不可用，需要检查 MCP 日志和 ZLMediaKit 流列表。 |

## 9. 调用流程建议

### 实时视频

1. 调用 `list_cameras` 获取摄像头列表。
2. 选择 `cameraId`。
3. 调用 `get_live_stream`。
4. 客户端使用返回的 `url` 播放视频。

### 历史录像

1. 调用 `list_cameras`，确认 `nvrBinding.bound` 为 `true`。
2. 调用 `search_recordings` 查询时间范围内的录像片段。
3. 选择一个 `recordingId`。
4. 调用 `get_recording_stream` 获取 FLV/HLS 播放地址。
5. 客户端使用返回的 `.flv` 或 `.m3u8` URL 播放视频。

## 10. 部署示例

`.env` 示例：

```bash
VIDEOAI_MCP_PLAYBACK_TTL_SECONDS=1800
PERSON_API_BASE_URL=http://192.168.11.192:18890
HIKVISION_NVR_BASE_URL=http://192.168.1.64
HIKVISION_NVR_USERNAME=admin
HIKVISION_NVR_PASSWORD=change-me
HCNETSDK_HOST=192.168.11.198
HCNETSDK_PORT=8000
HCNETSDK_USERNAME=admin
HCNETSDK_PASSWORD=cisdi123
HCNETSDK_CHANNEL=1
HCNETSDK_DOWNLOAD_NVR_HOSTS=10.10.7.252,10.10.7.253
HCNETSDK_DOWNLOAD_PORT=8000
HCNETSDK_DOWNLOAD_USERNAME=admin
HCNETSDK_DOWNLOAD_PASSWORD=change-me
HCNETSDK_DOWNLOAD_CHANNEL=1
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
