# VideoAI Monitoring MVP

单机 Docker GPU 版视频监控人脸识别 MVP。

## 功能

- ZLMediaKit 接入本机摄像头并提供直播流。
- Triton Inference Server 以 explicit model control 方式托管 SCRFD-10GF 和 ArcFace/MobileFaceNet 模型。
- Spring Boot 后端管理摄像头、人脸库、识别事件和 Triton 模型服务。
- Python worker 负责视频采样、人脸检测、对齐、向量提取和事件上报。
- React 前端提供监控、数字 PTZ、人脸库 CRUD、事件列表和模型管理页面。

## 启动

```bash
cp .env.example .env
docker compose up --build
```

只启动管理后台、数据库和 ZLMediaKit：

```bash
docker compose up --build -d postgres zlm backend frontend
```

启动 Triton 和 worker 推理链路：

```bash
docker compose --profile inference up --build -d
```

前端：http://localhost:5173

后端：http://localhost:8081

ZLMediaKit：http://localhost:8080

MCP Server：http://localhost:8091/mcp

Triton：http://localhost:8000

## 模型目录

将模型文件放入：

- `infra/model_repository/scrfd_10g/1/model.onnx`
- `infra/model_repository/arcface_mbf/1/model.onnx`
- `infra/model_repository/arcface_r50/1/model.onnx`

默认人脸识别模型是 InsightFace `buffalo_s/w600k_mbf.onnx`，即 MobileFaceNet 版本，文件约 13 MB，仓库内已放在 `arcface_mbf` 目录，Triton 输入为 `input.1`，输出为 `516`。如需重新下载：

```bash
scripts/download_arcface_mbf.sh
```

下载来源默认使用 Hugging Face 镜像：`https://hf-mirror.com/deepghs/insightface/resolve/main/buffalo_s/w600k_mbf.onnx`，SHA256 为 `9cc6e4a75f0e2bf0b1aed94578f144d15175f357bdc05e815e5c4a02b319eb4f`。

仓库内的 `config.pbtxt` 是 InsightFace 常见 ONNX 导出名称的模板。不同导出版本的 input/output 名称可能不同，首次加载失败时在前端模型管理页查看 Triton 错误，并按实际 ONNX 名称调整配置。启动推理链路后，在前端“模型管理”页加载 `scrfd_10g` 和 `arcface_mbf`。

## 摄像头

Linux 主机可用 `/dev/video0`。Windows/WSL2 通常不会把内置摄像头暴露为 `/dev/video0`，建议先在 Windows 侧把摄像头推成 RTSP/RTMP/HTTP 流，再在页面新增摄像头时填流地址。摄像头源填 `/dev/video0` 时，后端会通过 ZLMediaKit `setServerConfig` 写入 `ffmpeg.v4l2_cmd`，再通过 `addFFmpegSource` 启动 FFmpeg 推流。

## MCP Server

`mcp-server` 提供摄像头与海康 NVR 录像查询工具，默认使用 streamable HTTP：

```bash
docker compose up --build -d backend zlm mcp-server
```

在 `.env` 中配置海康 NVR：

```bash
HIKVISION_NVR_BASE_URL=http://192.168.1.64
HIKVISION_NVR_USERNAME=admin
HIKVISION_NVR_PASSWORD=change-me
```

可用 MCP tools：

- `list_cameras`：查询摄像头列表和 NVR 绑定信息。
- `get_live_stream`：返回摄像头实时播放 URL。
- `search_recordings`：按 `cameraId/startTime/endTime` 查询海康 NVR 历史录像。
- `get_recording_stream`：返回历史录像的短期 HLS 播放 URL。

历史录像查询要求摄像头配置 `nvrTrackId` 或 `nvrChannel`。NVR 凭据只保存在服务端环境变量中，MCP 响应不会返回带凭据的原始播放地址。
