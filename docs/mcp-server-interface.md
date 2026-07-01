# VideoAI MCP Server 接口说明书

## 1. 概述

VideoAI MCP Server 用于向 MCP 客户端暴露视频监控能力：

- 查询 VideoAI 摄像头列表。
- 获取指定摄像头实时视频播放地址。
- 查询海康 NVR 历史录像。
- 获取历史录像短期 HLS 播放地址。

视频字节流不通过 MCP 协议传输。MCP tools 只返回播放 URL，实际播放由 HTTP/ZLMediaKit 等媒体服务完成。

## 2. 服务信息

默认服务名：

```text
videoai-monitoring
```

默认 MCP 入口：

```text
http://localhost:8091/mcp
```

默认传输方式：

```text
streamable-http
```

可选传输方式由 `VIDEOAI_MCP_TRANSPORT` 配置，当前实现支持 FastMCP 的 `stdio`、`sse`、`streamable-http`。

## 3. 依赖服务

MCP Server 依赖以下服务：

- VideoAI Backend：读取摄像头列表、获取摄像头详情、启动直播。
- ZLMediaKit：把海康 NVR 回放流转为 HLS 播放地址。
- Hikvision NVR ISAPI：查询历史录像。

## 4. 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `VIDEOAI_BACKEND_URL` | `http://localhost:8081` | VideoAI 后端地址。Docker Compose 中默认为 `http://backend:8081`。 |
| `VIDEOAI_ZLM_HTTP_URL` | `http://localhost:8080` | ZLMediaKit 内部 API 地址。 |
| `VIDEOAI_ZLM_PUBLIC_HTTP_URL` | 同 `VIDEOAI_ZLM_HTTP_URL` | 返回给客户端的公网/宿主机播放地址前缀。 |
| `VIDEOAI_ZLM_SECRET` | 项目默认 secret | ZLMediaKit API secret。 |
| `VIDEOAI_ZLM_RTMP_PUSH_BASE` | `rtmp://localhost/live` | 转推历史回放流的 RTMP 目标前缀。 |
| `HIKVISION_NVR_BASE_URL` | 空 | 海康 NVR 地址，例如 `http://192.168.1.64`。 |
| `HIKVISION_NVR_USERNAME` | 空 | 海康 NVR 用户名。 |
| `HIKVISION_NVR_PASSWORD` | 空 | 海康 NVR 密码。 |
| `VIDEOAI_MCP_PLAYBACK_TTL_SECONDS` | `300` | 历史录像缓存和播放 URL 的默认有效期，单位秒。 |
| `VIDEOAI_MCP_REQUEST_TIMEOUT_SECONDS` | `15` | 外部 HTTP 请求超时时间，单位秒。 |
| `VIDEOAI_MCP_HOST` | `0.0.0.0` | MCP Server 监听地址。 |
| `VIDEOAI_MCP_PORT` | `8091` | MCP Server 监听端口。 |
| `VIDEOAI_MCP_TRANSPORT` | `streamable-http` | MCP 传输方式。 |

## 5. 摄像头 NVR 绑定字段

历史录像查询依赖摄像头上的 NVR 绑定信息。摄像头对象新增以下可选字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `nvrId` | `string|null` | NVR 标识，用于区分设备或做展示。 |
| `nvrChannel` | `string|null` | NVR 通道号。未配置 `nvrTrackId` 时可作为查询 track ID 使用。 |
| `nvrTrackId` | `string|null` | 海康 ISAPI 查询使用的 track ID，优先级高于 `nvrChannel`。 |
| `nvrStreamType` | `string|null` | 码流类型，例如 `main`、`sub`，当前主要用于元数据返回。 |

`search_recordings` 要求摄像头至少配置 `nvrTrackId` 或 `nvrChannel`。

## 6. Tools

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
| `livePlaybackUrl` | `string` | 实时流播放地址。 |
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

查询指定摄像头在海康 NVR 中的历史录像片段。

#### 输入参数

```json
{
  "cameraId": "6f1d3f34-7ab1-4d7e-9f1e-f3d0a7b9c101",
  "startTime": "2026-06-22T01:00:00Z",
  "endTime": "2026-06-22T02:00:00Z",
  "limit": 50
}
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `cameraId` | `string` | 是 | 无 | 摄像头 ID。 |
| `startTime` | `string` | 是 | 无 | 查询开始时间，ISO 8601 格式。 |
| `endTime` | `string` | 是 | 无 | 查询结束时间，ISO 8601 格式，必须晚于 `startTime`。 |
| `limit` | `integer` | 否 | `50` | 最大返回数量，服务端限制为 `1` 到 `200`。 |

#### 时间格式

推荐使用 UTC ISO 8601：

```text
2026-06-22T01:00:00Z
```

也可使用带时区偏移的格式：

```text
2026-06-22T09:00:00+08:00
```

#### 返回值

```json
[
  {
    "recordingId": "b7d7f2e07d1e4c8d8d8c8b1c1a9a0f22",
    "cameraId": "6f1d3f34-7ab1-4d7e-9f1e-f3d0a7b9c101",
    "cameraName": "Gate Camera",
    "trackId": "101",
    "startTime": "2026-06-22T01:00:00+00:00",
    "endTime": "2026-06-22T01:10:00+00:00",
    "source": "hikvision_nvr_recording",
    "metadata": {
      "nvrId": "main-nvr",
      "nvrChannel": "1",
      "nvrStreamType": "main"
    }
  }
]
```

#### 安全说明

返回值不包含海康 NVR 的 `playbackURI`，也不会返回用户名或密码。`recordingId` 是服务端生成的短期缓存 ID，用于后续调用 `get_recording_stream`。

### 6.4 `get_recording_stream`

获取某个历史录像片段的短期 HLS 播放地址。

#### 输入参数

```json
{
  "recordingId": "b7d7f2e07d1e4c8d8d8c8b1c1a9a0f22",
  "format": "hls"
}
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `recordingId` | `string` | 是 | 无 | `search_recordings` 返回的录像 ID。 |
| `format` | `"hls"` | 否 | `hls` | 当前仅支持 HLS。 |

#### 返回值

```json
{
  "url": "http://localhost:8080/live/recording-b7d7f2e07d1e4c8d8d8c8b1c1a9a0f22.m3u8",
  "format": "hls",
  "expiresAt": "2026-06-22T02:05:00+00:00",
  "source": "hikvision_nvr_recording",
  "metadata": {
    "nvrId": "main-nvr",
    "nvrChannel": "1",
    "nvrStreamType": "main",
    "cameraId": "6f1d3f34-7ab1-4d7e-9f1e-f3d0a7b9c101",
    "cameraName": "Gate Camera",
    "recordingId": "b7d7f2e07d1e4c8d8d8c8b1c1a9a0f22",
    "trackId": "101",
    "startTime": "2026-06-22T01:00:00+00:00",
    "endTime": "2026-06-22T01:10:00+00:00"
  }
}
```

#### 行为说明

- `recordingId` 必须来自同一 MCP Server 实例近期的 `search_recordings` 结果。
- 默认缓存有效期为 `VIDEOAI_MCP_PLAYBACK_TTL_SECONDS`，默认 `300` 秒。
- 如果缓存过期，需要重新调用 `search_recordings`。
- 调用时会通过 ZLMediaKit `addFFmpegSource` 把 NVR 回放地址转推为 HLS。

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
| ZLMediaKit 拒绝转推 | `ZLMediaKit rejected recording source: ...`。 |

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
4. 调用 `get_recording_stream` 获取 HLS 播放地址。
5. 客户端使用返回的 `.m3u8` URL 播放视频。

## 10. 部署示例

`.env` 示例：

```bash
VIDEOAI_MCP_PLAYBACK_TTL_SECONDS=300
HIKVISION_NVR_BASE_URL=http://192.168.1.64
HIKVISION_NVR_USERNAME=admin
HIKVISION_NVR_PASSWORD=change-me
```

启动：

```bash
docker compose up --build -d backend zlm mcp-server
```

MCP 客户端连接：

```text
http://localhost:8091/mcp
```
