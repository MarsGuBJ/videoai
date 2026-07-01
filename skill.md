# VideoAI 视频查询 MCP 技能

## 概述

通过 VideoAI MCP Server 查询实时摄像头列表、获取实时视频流、搜索历史录像、获取录像回放地址、算法布控、获取布控结果。所有接口返回 JSON 结构化数据及属性化 XML 标签。

## Output Contract

- 所有工具调用的输出**仅返回 `xml` 字段内容**，不输出 JSON 的 `data` 字段
- XML 标签名与工具一一对应：`list_cameras` → `<sxin-camera-list>`，`get_live_stream` → `<sxin-camera-flow>`，`search_recordings` → `<sxin-video-list>`，`get_recording_stream` → `<sxin-video-file>`
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

### 3. search_recordings — 查询历史录像

按时间范围搜索 NVR 上的录像文件。支持三种查询模式：
- 指定 `cameraId`：按摄像头绑定的 NVR 通道查询
- 指定 `trackId`（不传 `cameraId`）：直接按通道号查询
- 两者都不传：遍历所有 58 个通道（101~158）

当 ISAPI 接口不可用时，自动降级为 RTSP 直连模式（`source: hikvision_rtsp_fallback`），返回覆盖完整时间范围的单条录像片段，同时携带 `snapshotUrl` 等回放所需元数据。

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `cameraId` | string | 否 | 摄像头 ID，与 trackId 二选一 |
| `trackId` | string | 否 | NVR 通道号（如 101），与 cameraId 二选一 |
| `startTime` | string | 否 | 开始时间，ISO 8601 格式（默认当天 00:00:00） |
| `endTime` | string | 否 | 结束时间，ISO 8601 格式（默认当前时间） |
| `limit` | int | 否 | 最大返回数（默认 50，上限 200） |

**XML 响应（ISAPI 模式）**：
```xml
<?xml version="1.0" encoding="UTF-8"?>
<sxin-video-list count="2">
 <recording
   recordingId="abc123def456..."
   cameraId="95fb9b8d-d3a8-4ab6-b0cd-c874b67024c4"
   cameraName="1205实验室"
   trackId="101"
   startTime="2026-06-25T10:00:00+08:00"
   endTime="2026-06-25T10:05:00+08:00"
   source="hikvision_nvr_recording"
   nvrId="192.168.11.251">
  </recording>
</sxin-video-list>
```

**XML 响应（RTSP 降级模式）**：
```xml
<?xml version="1.0" encoding="UTF-8"?>
<sxin-video-list count="1">
 <recording
   recordingId="7102c405563dd47a472948f353802e27"
   cameraId="test-101"
   cameraName="NVR-101"
   trackId="101"
   startTime="2026-06-29T00:00:00+00:00"
   endTime="2026-06-29T23:59:59+00:00"
   source="hikvision_rtsp_fallback"
   nvrId="192.168.11.251">
  </recording>
</sxin-video-list>
```

**属性说明**：

| 属性 | 说明 |
|------|------|
| `recordingId` | 录像唯一标识，用于 get_recording_stream |
| `startTime` / `endTime` | 录像起止时间 |
| `trackId` | NVR 通道号 |
| `nvrId` | NVR 设备标识 |
| `source` | `hikvision_nvr_recording`（ISAPI）/ `hikvision_rtsp_fallback`（RTSP 降级） |

---

### 4. get_recording_stream — 获取录像回放地址

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `recordingId` | string | 是 | 从 search_recordings 获取的录像 ID |
| `format` | string | 否 | 播放格式（默认 "hls"，RTSP 降级录像返回 "mjpeg"） |

**XML 响应（HLS 回放）**：
```xml
<?xml version="1.0" encoding="UTF-8"?>
<sxin-video-file
  url="http://192.168.11.194:5174/live/recording-abc123.m3u8"
  format="hls"
  source="hikvision_nvr_recording"
  expiresAt="2026-06-25T10:15:00+00:00"
  cameraId="95fb9b8d-d3a8-4ab6-b0cd-c874b67024c4"
  cameraName="1205实验室"
  recordingId="abc123def456..."
  trackId="101"
  startTime="2026-06-25T10:00:00+08:00"
  endTime="2026-06-25T10:05:00+08:00">
</sxin-video-file>
```

**XML 响应（MJPEG 快照回放，RTSP 降级模式）**：
```xml
<?xml version="1.0" encoding="UTF-8"?>
<sxin-video-file
  url="http://192.168.11.194:8100/stream.mjpeg"
  format="mjpeg"
  source="hikvision_http_snapshot"
  expiresAt="2026-06-29T14:22:00+00:00"
  cameraId="test-101"
  cameraName="NVR-101"
  recordingId="7102c405563dd47a472948f353802e27"
  trackId="101"
  startTime="2026-06-29T00:00:00+00:00"
  endTime="2026-06-29T23:59:59+00:00">
</sxin-video-file>
```

**属性说明**：

| 属性 | 说明 |
|------|------|
| `url` | 回放流地址（HLS .m3u8 或 MJPEG ） |
| `format` | 播放格式：`hls`（ISAPI 模式）/ `mjpeg`（RTSP 降级模式，~6fps 快照流） |
| `expiresAt` | URL 过期时间（默认 300 秒），过期后需重新调用 |
| `startTime` / `endTime` | 录像片段起止时间 |

---

### 5. upload_face_image — 算法布控

将附件上传的图片通过skill:image-to-base64转为base64编码，上传 base64 编码到人脸库。人脸库只能保存一张图片，新上传会覆盖旧图片。返回 faceId 用于后续获取布控结果。

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `imageBase64` | string | 是 | 图片的 base64 编码数据 |
| `cameraId` | string | 是 | 摄像头 ID（当前为预留参数） |
| `modelName` | string | 是 | 算法模型名称（如 scrfd_10g），当前为预留参数 |
| `name` | string | 否 | 人脸姓名（默认 "人脸库照片"） |

**响应**：
```json
{
  "faceId": "5e0a5730-a07e-4404-9774-a75621642542"
}
```

---

### 6. query_face_matches — 获取算法布控结果

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
| `videoai://recordings/{recordingId}` | 获取缓存的录像记录（不含 playbackUri） |

---

## 典型调用流程

### 查看实时画面

1. `list_cameras` → 获取摄像头 ID 和名称
2. 用户选择摄像头
3. `get_live_stream(cameraId="{id}")` → 获取 `<sxin-camera-flow url="...">` 播放

### 回放历史录像

三种查询方式：

1. **按摄像头查询**（摄像头已绑定 NVR 通道）：
   1. `list_cameras` → 确认摄像头有 `nvrBinding="true"`
   2. `search_recordings(cameraId="{id}", startTime="...", endTime="...")` → 获取 `<sxin-video-list>`
   3. `get_recording_stream(recordingId="{id}")` → 获取播放 URL

2. **按通道号直接查询**（无需摄像头）：
   1. `search_recordings(trackId="101", startTime="...", endTime="...")` → 直接搜索指定通道

3. **遍历全部通道**（NVR 所有 58 路）：
   1. `search_recordings(startTime="...", endTime="...")` → 自动遍历 101~158，返回按时间分片的录像片段

### 算法布控与人脸识别

1. `upload_face_image(imageBase64="...", cameraId="...", modelName="scrfd_10g", name="姓名")` → 提交布控照片，获取 `faceId`
2. 等待实时识别结果（多路摄像头持续运行中）
3. `query_face_matches(faceId="{id}", limit=10)` → 获取布控结果列表
4. 不传 faceId 则返回全局最新 10 条布控结果

---

## NVR 信息

| 属性 | 值 |
|------|------|
| 设备型号 | Hikvision DS-8664N-K8 |
| 固件版本 | V3.4.106 |
| 地址 | http://192.168.11.251 |
| 录像通道 | 58 路，trackId 101~158 |
| 录像查询协议 | ISAPI / RTSP 直连 |
| 回放协议 | HTTP MJPEG 快照流 |

---

## 注意事项

1. `livePlaybackUrl` / `url` 均为公网可访问的 HLS 地址，可直接嵌入 `<video>` 播放器
2. 录像回放 URL 有时效性（`expiresAt`），过期后需重新调用 `get_recording_stream`
3. 摄像头若无 `nvrBinding="true"`，则不支持录像查询
4. 人脸库仅保留一张布控照片，新上传会覆盖旧照片
5. 布控结果依赖 Triton 推理服务（SCRFD + ArcFace），匹配相似度阈值 0.55
6. 所有 XML 数据均在响应的 `xml` 字段中，`data` 字段包含等价的 JSON 结构化数据
