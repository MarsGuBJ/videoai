# 设备管理对外开放接口说明书

## 概述

设备管理模块对外提供两个匿名接口（无需鉴权），供第三方平台获取设备列表和实时视频流：

| 序号 | 接口 | 方法 | 说明 |
|------|------|------|------|
| 1 | `/api/open/devices` | GET | 获取全部设备（在线 + 离线）列表 |
| 2 | `/api/open/devices/{deviceId}/live.flv` | GET | 获取指定设备的实时 FLV 视频流 |

接口路径均为 URL 路径，调用时拼接服务的 Base URL（默认端口 `8081`，以实际部署为准），例如：

```
http://<host>:8081/api/open/devices
```

设计要点：

- **匿名访问**：两个接口均不要求登录或 Token，请勿暴露到不可信网络。
- **信息脱敏**：列表仅返回名称、位置、在线状态和基础信息，不暴露拉流地址、用户名、密码等内部/敏感字段。
- **按需建流**：视频流链接是固定地址，请求时才动态建立视频流（未开播的设备会自动开播），无需调用方预先触发。

---

## 一、获取设备列表

### GET /api/open/devices

返回平台全部设备（含在线和离线）的列表。

#### 请求参数

无。

#### 返回值

**成功 (200)**，`Content-Type: application/json`

```json
[
    {
        "deviceId": "3f6c2e54-9a1b-4c8d-9e0f-1a2b3c4d5e6f",
        "name": "东门入口枪机",
        "area": "厂区/东门",
        "onlineStatus": "ONLINE",
        "streamUrl": "/api/open/devices/3f6c2e54-9a1b-4c8d-9e0f-1a2b3c4d5e6f/live.flv",
        "basicInfo": {
            "deviceCode": "CAM-0001",
            "protocol": "GB28181",
            "vendor": "海康威视",
            "ip": "192.168.1.101",
            "port": "554",
            "serialNumber": "DS-2CD3T47DWD-L",
            "deviceCategory": "摄像机",
            "deviceType": "枪机",
            "channelName": "通道1",
            "gbCode": "34020000001320000001",
            "description": "东门入口监控",
            "nvrId": "NVR-01",
            "nvrChannel": "3",
            "nvrStreamType": "主码流"
        }
    }
]
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `deviceId` | string (UUID) | 设备唯一标识，视频流接口的路径参数 |
| `name` | string | 设备名称 |
| `area` | string | 设备位置（区域路径） |
| `onlineStatus` | string | 在线状态：`ONLINE` 在线、`OFFLINE` 离线、`UNKNOWN` 未知（地址不可解析或为内部推流地址，待人工确认） |
| `streamUrl` | string \| null | 固定视频流链接（相对路径，拼接 Base URL 后使用）；设备未配置拉流地址时为 `null` |
| `basicInfo` | object | 设备基础信息（已剔除凭据等敏感字段） |
| `basicInfo.deviceCode` | string | 设备编码 |
| `basicInfo.protocol` | string | 接入协议（如 `GB28181`、`RTSP` 等） |
| `basicInfo.vendor` | string | 厂商 |
| `basicInfo.ip` | string | 设备 IP |
| `basicInfo.port` | string | 设备端口 |
| `basicInfo.serialNumber` | string | 序列号 |
| `basicInfo.deviceCategory` | string | 设备大类 |
| `basicInfo.deviceType` | string | 设备型号/类型 |
| `basicInfo.channelName` | string | 通道名称 |
| `basicInfo.gbCode` | string | 国标编码 |
| `basicInfo.description` | string | 设备描述 |
| `basicInfo.nvrId` | string | 所属 NVR 标识（直连设备为 null） |
| `basicInfo.nvrChannel` | string | NVR 通道号 |
| `basicInfo.nvrStreamType` | string | NVR 码流类型（主码流/子码流） |

#### 调用示例

```bash
curl http://<host>:8081/api/open/devices
```

---

## 二、获取实时视频流

### GET /api/open/devices/{deviceId}/live.flv

以 HTTP-FLV 方式返回指定设备的实时视频流（`Content-Type: video/x-flv`），可直接接入 flv.js 等播放器。

链接为固定地址，**请求时才动态建流**：若设备当前未开播，服务端会先自动为其挂流（含可推导的子码流），再代理返回流数据；流刚启动时在启动超时窗口内会自动重试等待就绪，调用方无需关心建流过程。

#### 路径参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `deviceId` | string (UUID) | 是 | 设备唯一标识，来自设备列表接口的 `deviceId` 字段 |

#### 返回值

**成功 (200)**

- 响应头：`Content-Type: video/x-flv`
- 响应体：持续的 FLV 流数据（长连接，流式传输直至断开）

**失败**

| 状态码 | 说明 |
|--------|------|
| 400 | 该设备未配置拉流地址，无法提供视频流（列表中 `streamUrl` 为 `null` 的设备） |
| 404 | 设备不存在，或流在启动超时窗口内仍未就绪 |
| 502 | 流媒体服务不可用（连接失败或请求异常） |

#### 调用示例

```bash
# 拉流（持续输出流数据，Ctrl+C 停止）
curl http://<host>:8081/api/open/devices/3f6c2e54-9a1b-4c8d-9e0f-1a2b3c4d5e6f/live.flv
```

```html
<!-- flv.js 播放示例 -->
<script src="https://cdn.jsdelivr.net/npm/flv.js/dist/flv.min.js"></script>
<video id="video" controls autoplay muted></video>
<script>
  const player = flvjs.createPlayer({
    type: 'flv',
    url: 'http://<host>:8081/api/open/devices/3f6c2e54-9a1b-4c8d-9e0f-1a2b3c4d5e6f/live.flv'
  });
  player.attachMediaElement(document.getElementById('video'));
  player.load();
  player.play();
</script>
```

#### 使用建议

- 推荐流程：先调接口一获取设备列表，取 `streamUrl` 拼接 Base URL 播放；`streamUrl` 为 `null` 的设备不可播放，应在界面上禁用。
- 视频流为长连接，播放结束或页面关闭时应主动断开，避免占用服务端流资源。
