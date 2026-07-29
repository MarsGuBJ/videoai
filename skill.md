# VideoAI 视频查询 MCP 技能

## 概述

通过 VideoAI MCP Server 查询实时摄像头列表、获取实时视频流、搜索历史录像、获取录像回放地址、算法布控、获取布控结果。所有接口返回 JSON 结构化数据及属性化 XML 标签。

## Output Contract

- 所有工具调用的输出**仅返回 `xml` 字段内容**，不输出 JSON 的 `data` 字段
- XML 标签名与工具一一对应：`list_cameras` → `<sxin-camera-list>`，`get_live_stream` → `<sxin-camera-flow>`，`search_recordings` → `<sxin-video-list>`，`dino_events` → `<sxin-dino-event-list>`
- 禁止在最终回复中输出原始 JSON 结构或 `data` 数组
- 如果 XML 中无数据（如 count="0"），直接告知用户"无结果"，不输出空 XML

## MCP 接入

```json
{
  "mcpServers": {
    "videoai": {
      "url": "http://192.168.11.194:8097/mcp",
      "transport": "streamable-http"
    }
  }
}
```

## 可用工具

共 6 个 Tool + 2 个 Resource。

### 1. list_cameras — 查询实时摄像头列表

返回所有实时摄像头（NVR 专用录像通道自动排除）。

**参数**：无

**XML 响应**：
```xml
<?xml version="1.0" encoding="UTF-8"?>
<sxin-camera-list count="2">
 <camera
   id="c71f4f5d-065a-40d8-b81a-72124c94b131"
   name="金山12楼门口"
   status="RUNNING"
   livePlaybackUrl="http://192.168.11.194:5174/live/camera-1782139888691571790/hls.m3u8"
   sourceUrl="rtmp://localhost:1945/live/camera-1782139888691571790"
   nvrBinding="false">
  </camera>
 <camera
   id="95fb9b8d-d3a8-4ab6-b0cd-c874b67024c4"
   name="1205实验室"
   status="RUNNING"
   livePlaybackUrl="http://192.168.11.194:5174/live/cam65/hls.m3u8"
   sourceUrl="rtmp://localhost:1945/live/cam65"
   nvrBinding="true">
  </camera>
</sxin-camera-list>
```

**属性说明**：

| 属性 | 说明 |
|------|------|
| `id` | 摄像头唯一标识，用于 get_live_stream / search_recordings |
| `name` | 摄像头名称 |
| `status` | RUNNING / STOPPED |
| `livePlaybackUrl` | HLS 直播流地址，可直接播放 |
| `sourceUrl` | 内部源地址 |
| `nvrBinding` | true=已绑定 NVR 通道，可查询录像 |

---

### 2. get_live_stream — 获取实时视频流

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `cameraId` | string | 是 | 摄像头 ID |
| `autoStart` | boolean | 否 | 是否自动启动（默认 true） |

**XML 响应**：
```xml
<?xml version="1.0" encoding="UTF-8"?>
<sxin-camera-flow
  url="http://192.168.11.194:5174/live/cam65/hls.m3u8"
  format="hls"
  source="live"
  expiresAt=""
  cameraId="95fb9b8d-d3a8-4ab6-b0cd-c874b67024c4"
  cameraName="1205实验室"
  status="RUNNING">
</sxin-camera-flow>
```

**属性说明**：

| 属性 | 说明 |
|------|------|
| `url` | 可直接播放的 HLS 流地址 |
| `format` | 流格式（hls） |
| `cameraName` | 摄像头名称 |
| `status` | 摄像头状态 |

---

### 3. search_recordings — 查询历史录像流

按时间范围从 `192.168.11.198:8000` 的通道 `1` 使用 HCNetSDK 回调取流，并通过 ZLMediaKit 代理成 FLV 播放地址。

只返回一条覆盖完整时间范围的录像记录。`autoProxy=true` 时由 ffmpeg 把 HCNetSDK 回调码流转推至 ZLMediaKit，并返回 FLV `url`。当前设备实测同通道稳定支持 2 路并发回放流。

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `cameraId` | string | 否 | 兼容字段，演示模式下不决定 NVR 查询通道 |
| `trackId` | string | 否 | 兼容字段，当前固定使用 192.168.11.198 通道 1 |
| `startTime` | string | 否 | 开始时间，ISO 8601 格式（默认当天 00:00:00） |
| `endTime` | string | 否 | 结束时间，ISO 8601 格式（默认当前时间） |
| `limit` | int | 否 | 兼容字段，当前固定只返回 1 条 |

**XML 响应**：
```xml
<?xml version="1.0" encoding="UTF-8"?>
<sxin-video-list count="2">
 <recording
   recordingId="abc123def456..."
   cameraId="192.168.11.198-channel-1"
   cameraName="IPC-192.168.11.198-1"
   trackId="1"
   startTime="2026-06-25T10:00:00+08:00"
   endTime="2026-06-25T11:00:00+08:00"
   source="hikvision_hcnetsdk_playback"
   url="http://example.com/live/hcn-7102c405563d-a1b2c3d4.live.flv"
   nvrId="">
  </recording>
</sxin-video-list>
```

**属性说明**：

| 属性 | 说明 |
|------|------|
| `recordingId` | 录像唯一标识 |
| `startTime` / `endTime` | 录像起止时间 |
| `trackId` | 固定通道 `1` |
| `source` | `hikvision_hcnetsdk_playback` |
| `url` | **FLV 地址**，由 ffmpeg 把 HCNetSDK 回调码流转推至 ZLMediaKit，再由 ZLMediaKit 输出，浏览器可直接播放 |

---

### 4. download_recording — 下载历史录像 MP4

按时间范围从 `192.168.11.198:8000` 的通道 `1` 使用 `NET_DVR_GetFileByTime` 下载录像，转为 MP4 后保存到 MinIO，返回 MP4 文件 URL。

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `startTime` | string | 是 | 开始时间，ISO 8601 格式；无时区时按北京时间 |
| `endTime` | string | 是 | 结束时间，必须晚于 startTime；无时区时按北京时间 |

**HTTP 示例**：
```bash
curl -X POST http://192.168.11.194:8097/download_recording-http \
  -H 'Content-Type: application/json' \
  -d '{"startTime":"2026-07-14T11:22:10+08:00","endTime":"2026-07-14T11:23:10+08:00"}'
```

**返回要点**：

| 字段 | 说明 |
|------|------|
| `data[0].url` | MinIO MP4 文件 URL，例如 `http://192.168.11.194:9000/public/recordings/192.168.11.198/ch1/<recordingId>.mp4` |
| `data[0].format` | 固定为 `mp4` |
| `data[0].source` | `hikvision_hcnetsdk_download` |
| `data[0].metadata.objectName` | MinIO 对象名 |

---

### 5. dino_events — 查询 DINO 视觉事件

返回 10 条 DINO Object Detection 事件 mock 数据。

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `limit` | int | 否 | 返回条数（默认 10，最大 10） |

**XML 响应**：
```xml
<?xml version="1.0" encoding="UTF-8"?>
<sxin-dino-event-list count="10">
 <event
   eventId="dino-mock-001"
   eventSource="视觉平台"
   eventType="DINO Object Detection"
   eventStatus="有效"
   eventLevel="1"
   eventLocation="摄像头101"
   occurredAt="2026-07-07T09:00:00+08:00"
   reportedAt="2026-07-07T09:00:00+08:00"
   eventImage="data:image/svg+xml;charset=utf-8,..."
   eventDescription="无">
  </event>
</sxin-dino-event-list>
```

---

### 6. upload_face_image — 算法布控

通过图片 URL 上传人脸照片到人脸库，并按传入参数创建一个启用状态的人脸布控任务。MCP Server 会下载该 URL 指向的图片并写入人脸库；人脸库只能保存一张图片，新上传会覆盖旧图片。创建的布控任务会出现在布控任务页面，默认 `enabled=true` 且 `taskStatus=running`。

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `imageUrl` | string | 是 | 图片 URL，必须可由 MCP Server 访问 |
| `cameraId` | string | 是 | 摄像头 ID，布控任务会绑定到该摄像头 |
| `modelName` | string | 是 | 算法模型名称（如 scrfd_10g），作为布控任务流程名 |
| `name` | string | 否 | 人脸姓名，同时作为布控任务名称（默认 "人脸库照片"） |

**响应**：
```json
{
  "faceId": "5e0a5730-a07e-4404-9774-a75621642542",
  "deploymentTaskId": "6f3d3c25-3d75-4c28-bd4f-0c7184f5487b",
  "deploymentTask": {
    "enabled": true,
    "taskStatus": "running",
    "cameraIds": ["camera-id"]
  }
}
```

---

### 7. query_face_matches — 获取算法布控结果

查询多路实时识别匹配上的人像数据。按视频时间倒序排列。

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `faceId` | string | 否 | 从算法布控（upload_face_image）获取的图片 ID；不传则返回全局最新 10 条 |
| `limit` | int | 否 | 返回条数（默认 10，最大 10） |

**响应**：
```json
{
  "data": [
    {
      "id": "...",
      "cameraId": "...",
      "cameraName": "摄像头01",
      "profileName": "Linda",
      "similarity": 0.92,
      "videoTime": "2026-06-29T12:00:00Z",
      "facePhotoUrl": "/api/assets/faces/xxx.jpg",
      "snapshotUrl": "/api/assets/snapshots/xxx.jpg"
    }
  ],
  "count": 1
}
```

| 属性 | 说明 |
|------|------|
| `profileName` | 匹配到的人脸姓名 |
| `cameraName` | 出现在哪个摄像头 |
| `similarity` | 匹配相似度（0~1） |
| `videoTime` | 匹配时间 |

---

## Resources

| URI | 说明 |
|-----|------|
| `videoai://cameras/{cameraId}` | 获取单个摄像头详情 |
| `videoai://recordings/{recordingId}` | 获取缓存的录像记录（含 `url`） |

---

## 典型调用流程

### 查看实时画面

1. `list_cameras` → 获取摄像头 ID 和名称
2. 用户选择摄像头
3. `get_live_stream(cameraId="{id}")` → 获取 `<sxin-camera-flow url="...">` 播放

### 回放历史录像

两种查询方式：

1. **流式回放**：
   1. `search_recordings(startTime="...", endTime="...")` → 使用 HCNetSDK 回调推流，返回 FLV `url`

2. **下载 MP4**：
   1. `download_recording(startTime="...", endTime="...")` → 下载录像、转 MP4、上传 MinIO，返回 MP4 文件 `url`

### 算法布控与人脸识别

1. `upload_face_image(imageUrl="http://.../face.jpg", cameraId="...", modelName="scrfd_10g", name="姓名")` → 提交布控照片并创建默认开启的布控任务，获取 `faceId` 和 `deploymentTaskId`
2. 等待实时识别结果（多路摄像头持续运行中）
3. `query_face_matches(faceId="{id}", limit=10)` → 获取布控结果列表
4. 不传 faceId 则返回全局最新 10 条布控结果

---

## NVR 信息

| 属性 | 值 |
|------|------|
| 设备型号 | Hikvision IPC |
| 地址 | 192.168.11.198:8000 |
| 默认录像通道 | 1 |
| 录像查询协议 | HCNetSDK 私有协议 |
| 回放协议 | FLV（HCNetSDK 回调→FFmpeg→ZLMediaKit） |
| 下载协议 | MP4（NET_DVR_GetFileByTime→FFmpeg remux→MinIO） |

---

## 注意事项

1. `livePlaybackUrl` / `url` 均为可播放地址（直播 / 录像回放），浏览器、ffmpeg、VLC 等播放器可直接打开
2. 录像回放 `url` 由 ffmpeg 把 HCNetSDK 回调码流转 RTMP，再由 ZLMediaKit 输出 FLV；时延约 2-3 秒
3. `search_recordings(autoProxy=true)` 支持并发回放流，当前设备实测稳定并发上限为 2 路
4. `download_recording` 返回 MinIO MP4 文件链接，不占用长期回放流
5. 人脸库仅保留一张布控照片，新上传会覆盖旧照片
6. 布控结果依赖 Triton 推理服务（SCRFD + ArcFace），匹配相似度阈值 0.55
7. 所有 XML 数据均在响应的 `xml` 字段中，`data` 字段包含等价的 JSON 结构化数据
