---
name: video-search
description: 视频查询与回放 skill：用于用户查询摄像头列表、查看实时视频画面、搜索历史录像、播放录像回放等场景。支持 list_cameras / get_live_stream / search_recordings / get_recording_stream 四种 MCP 工具调用，输出 sxin-camera-list / sxin-camera-flow / sxin-video-list / sxin-video-file 四种 XML 标签。触发词包括:摄像头、录像、回放、视频、监控、直播、实时画面等。
---

# VideoAI 视频查询 MCP 使用技能

## 概述

通过 VideoAI MCP Server 查询实时摄像头、实时视频流、历史录像及录像回放。所有接口同时返回 JSON 结构化数据和 XML 格式摘要，适合 AI 代理解析和展示。

## MCP 服务信息

| 属性 | 值 |
|------|-----|
| 服务名 | `videoai-monitoring` |
| 入口 | `http://192.168.11.194:8097/mcp` |
| 传输 | `streamable-http` |

## 可用工具

### 1. list_cameras — 查询摄像头列表

**无参数**。返回所有已配置摄像头及 NVR 绑定信息。

**XML 格式**：
<sxin-camera-list count="2">
  <camera>
    <id>14a9a092-00e4-48db-8945-305f69d60d75</id>
    <name>摄像头-65</name>
    <status>RUNNING</status>
    <livePlaybackUrl>http://192.168.11.194:8082/live/cam65/hls.m3u8</livePlaybackUrl>
    <sourceUrl>rtmp://localhost:1945/live/cam65</sourceUrl>
    <nvrBinding>
      <bound>true</bound>
      <nvrId>cam65-nvr</nvrId>
      <nvrChannel>1</nvrChannel>
      <nvrTrackId>101</nvrTrackId>
      <nvrStreamType>main</nvrStreamType>
    </nvrBinding>
  </camera>
  <camera>
    <id>4e653058-16c5-4cc3-9422-b241a66c1238</id>
    <name>摄像头-198</name>
    <status>RUNNING</status>
    <livePlaybackUrl>http://192.168.11.194:8082/live/camera-1782139888691571790/hls.m3u8</livePlaybackUrl>
    <sourceUrl>rtmp://localhost:1945/live/camera-1782139888691571790</sourceUrl>
    <nvrBinding>
      <bound>false</bound>
      <nvrId/>
      <nvrChannel/>
      <nvrTrackId/>
      <nvrStreamType/>
    </nvrBinding>
  </camera>
</sxin-camera-list>

---

### 2. get_live_stream — 获取实时视频流

**参数**：
- `cameraId` (string, 必填) — 摄像头 ID
- `autoStart` (boolean, 默认 true) — 自动启动未运行的摄像头

**XML 格式**：
<sxin-camera-flow>
  <url>http://192.168.11.194:8082/live/cam65/hls.m3u8</url>
  <format>hls</format>
  <source>live</source>
  <expiresAt>null</expiresAt>
  <metadata>
    <cameraId>14a9a092-00e4-48db-8945-305f69d60d75</cameraId>
    <cameraName>摄像头-65</cameraName>
    <status>RUNNING</status>
    <streamApp>live</streamApp>
    <streamName>cam65</streamName>
  </metadata>
</sxin-camera-flow>

---

### 3. search_recordings — 查询历史录像

**参数**：
- `cameraId` (string, 必填) — 摄像头 ID（需绑定 NVR track/channel）
- `startTime` (string, 必填) — 开始时间，ISO 8601 格式（如 `2026-06-25T00:00:00+08:00`）
- `endTime` (string, 必填) — 结束时间
- `limit` (int, 默认 50) — 最大返回条数

**前置条件**：摄像头需配置 `nvrTrackId` 或 `nvrChannel`，且 NVR 有存储。

**XML 格式**：
<sxin-video-list count="2">
  <recording>
    <recordingId>abc123...</recordingId>
    <cameraId>14a9a092-00e4-48db-8945-305f69d60d75</cameraId>
    <cameraName>摄像头-65</cameraName>
    <trackId>101</trackId>
    <startTime>2026-06-25T10:00:00+08:00</startTime>
    <endTime>2026-06-25T10:05:00+08:00</endTime>
    <source>hikvision_nvr_recording</source>
    <metadata>
      <nvrId>cam65-nvr</nvrId>
      <nvrChannel>1</nvrChannel>
      <nvrStreamType>main</nvrStreamType>
    </metadata>
  </recording>
</sxin-video-list>

---

### 4. get_recording_stream — 获取历史录像播放流

**参数**：
- `recordingId` (string, 必填) — 从 search_recordings 获取的录像 ID
- `format` ("hls", 默认 hls) — 播放格式

**XML 格式**：
<sxin-video-file>
  <url>http://192.168.11.194:8082/live/recording-abc123.m3u8</url>
  <format>hls</format>
  <source>hikvision_nvr_recording</source>
  <expiresAt>2026-06-25T10:15:00+00:00</expiresAt>
  <metadata>
    <cameraId>14a9a092-00e4-48db-8945-305f69d60d75</cameraId>
    <cameraName>摄像头-65</cameraName>
    <recordingId>abc123...</recordingId>
    <trackId>101</trackId>
    <startTime>2026-06-25T10:00:00+08:00</startTime>
    <endTime>2026-06-25T10:05:00+08:00</endTime>
  </metadata>
</sxin-video-file>

---

## 调用流程示例

### 场景一：查看所有摄像头

用户: 列出所有摄像头
→ 调用 list_cameras()
→ 展示 <sxin-camera-list> XML 中的摄像头名称和状态


### 场景二：查看实时画面

用户: 打开摄像头-65的实时画面
→ 调用 list_cameras() 获取 cameraId
→ 调用 get_live_stream(cameraId="{id}")
→ 返回 <sxin-camera-flow> 中的 HLS URL，可嵌入播放器


### 场景三：查询历史录像

用户: 查询摄像头-65今天上午10点到11点的录像
→ 调用 list_cameras() 获取 cameraId
→ 调用 search_recordings(cameraId="{id}", startTime="2026-06-25T10:00:00+08:00", endTime="2026-06-25T11:00:00+08:00")
→ 展示 <sxin-video-list> 中的录像时间段


### 场景四：播放一段历史录像

用户: 打开第一个录像
→ 从 search_recordings 结果中获取 recordingId
→ 调用 get_recording_stream(recordingId="{id}")
→ 返回 <sxin-video-file> 中的 HLS URL


---

## 注意事项

1. NVR 录像查询要求摄像头已配置 NVR 绑定（`nvrTrackId` 或 `nvrChannel`）
2. 历史录像回放 URL 具有时效性（默认 300 秒），过期需重新调用 `get_recording_stream`
3. 摄像头如无 SD 卡或 NAS 存储，`search_recordings` 将返回空列表
4. XML 内容在响应的 `xml` 字段中，同时保留 `data` 字段的 JSON 结构化数据

## Output Contract

所有输出必须以 `sxin-*` 标签包裹。每次调用只允许输出**一个**标签（即四种场景中只选一种），不得混合输出多个标签。标签中的字段取自 MCP 工具返回的 `data` 和 `xml` 响应。

---

### 场景一：查看所有摄像头 → 只输出一个 `sxin-camera-list`

从 `list_cameras` 返回的 `data[]` 中提取每个摄像头的 `id`、`name`、`status`，组装为：

<sxin-camera-list count="2">
  <camera>
    <id>14a9a092-00e4-48db-8945-305f69d60d75</id>
    <name>金山12楼门口</name>
    <status>RUNNING</status>
  </camera>
  <camera>
    <id>4e653058-16c5-4cc3-9422-b241a66c1238</id>
    <name>1205实验室</name>
    <status>RUNNING</status>
  </camera>
</sxin-camera-list>

- `count` 属性：摄像头数量
- 每个 `<camera>` 必须包含 `id`、`name`、`status` 三个子元素

**失败/无数据时输出空标签**：

<sxin-camera-list count="0"></sxin-camera-list>

---

### 场景二：查看实时画面 → 只输出一个 `sxin-camera-flow`

从 `get_live_stream` 返回的 `data` 中提取 `url`、`format`、`source` 及 `metadata.cameraName`、`metadata.status`，组装为：

<sxin-camera-flow>
  <url>http://192.168.11.194:5174/live/camera-1782139888691571790/hls.m3u8</url>
  <format>hls</format>
  <source>live</source>
  <expiresAt>null</expiresAt>
  <metadata>
    <cameraId>c71f4f5d-065a-40d8-b81a-72124c94b131</cameraId>
    <cameraName>金山12楼门口</cameraName>
    <status>RUNNING</status>
  </metadata>
</sxin-camera-flow>

- `url` 为 HLS 直播流地址，用户可用播放器打开
- `metadata` 中必含 `cameraId`、`cameraName`、`status`

**失败/摄像头离线时输出空标签**：

<sxin-camera-flow></sxin-camera-flow>

---

### 场景三：查询历史录像 → 只输出一个 `sxin-video-list`

从 `search_recordings` 返回的 `data[]` 中提取每条录像的 `recordingId`、`cameraName`、`startTime`、`endTime`，组装为：

<sxin-video-list count="2">
  <recording>
    <recordingId>abc123...</recordingId>
    <cameraName>金山12楼门口</cameraName>
    <startTime>2026-06-25T10:00:00+08:00</startTime>
    <endTime>2026-06-25T10:05:00+08:00</endTime>
  </recording>
  <recording>
    <recordingId>def456...</recordingId>
    <cameraName>金山12楼门口</cameraName>
    <startTime>2026-06-25T11:00:00+08:00</startTime>
    <endTime>2026-06-25T11:05:00+08:00</endTime>
  </recording>
</sxin-video-list>

- `count` 属性：录像数量
- 每个 `<recording>` 必含 `recordingId`、`cameraName`、`startTime`、`endTime`

**失败/无录像时输出空标签**：

<sxin-video-list count="0"></sxin-video-list>

---

### 场景四：播放历史录像 → 只输出一个 `sxin-video-file`

从 `get_recording_stream` 返回的 `data` 中提取 `url`、`format`、`source` 及 `metadata` 中的摄像头和录像信息，组装为：

<sxin-video-file>
  <url>http://192.168.11.194:5174/live/recording-abc123.m3u8</url>
  <format>hls</format>
  <source>hikvision_nvr_recording</source>
  <expiresAt>2026-06-25T10:15:00+00:00</expiresAt>
  <metadata>
    <cameraId>c71f4f5d-065a-40d8-b81a-72124c94b131</cameraId>
    <cameraName>金山12楼门口</cameraName>
    <recordingId>abc123</recordingId>
    <trackId>101</trackId>
    <startTime>2026-06-25T10:00:00+08:00</startTime>
    <endTime>2026-06-25T10:05:00+08:00</endTime>
  </metadata>
</sxin-video-file>

- `url` 为 HLS 播放流地址，有时效性（默认 300 秒）
- `metadata` 中必含 `cameraId`、`cameraName`、`recordingId`

**失败时输出空标签**：

<sxin-video-file></sxin-video-file>
