# 接口规范

## 环境地址

下文接口路径均为 URL 路径（统一前缀 `/vlm-application`），调用时拼接对应环境的 Base URL：

| 环境 | Base URL | 可用搜法 | 测试图片 |
|------|------|------|------|
| 192 研发 | `http://192.168.11.192:15501` | reid + vlm | `http://192.168.11.194:9000/zhcs/event/image/202607/bc433619a458f10a3fbbc3a970467ede_d5a2c4b1ef4499aad3867ed6a9c5899e_1782956484331_origin.jpg` |
| 枢纽港现场 | `http://10.10.3.100:15501` | reid + vlm | `http://10.10.3.100:9000/zhcs/event/image/202609/0f9605163080d869170649af0ad82041_6ca1e5ab23a26fc26b8ad756c90ee0dc_1788215708038_origin.jpg` |
| 团结湖现场 | `http://172.17.136.189:15501` | **仅 reid** | `http://172.21.201.40:9000/zhcs/event/image/202609/6743dc2ee4615fa52b552260e4a79872_7fe9a0d976c286b89f72bdec906e97d2_origin_1789888242337.jpg` |

> 团结湖无 vllm 大模型服务，`search_method` 只能省略或 `"reid"`。环境详情见 [环境清单.md](./环境清单.md)。

示例（人员检测，替换 Base URL / image_url 即可切换环境）：

```bash
# 192 研发
curl -X POST http://192.168.11.192:15501/vlm-application/search/detectPersons \
     -H "Content-Type: application/json" \
     -d '{"image_url": "http://192.168.11.194:9000/zhcs/event/image/202607/bc433619a458f10a3fbbc3a970467ede_d5a2c4b1ef4499aad3867ed6a9c5899e_1782956484331_origin.jpg"}'

# 枢纽港现场
curl -X POST http://10.10.3.100:15501/vlm-application/search/detectPersons \
     -H "Content-Type: application/json" \
     -d '{"image_url": "http://10.10.3.100:9000/zhcs/event/image/202609/0f9605163080d869170649af0ad82041_6ca1e5ab23a26fc26b8ad756c90ee0dc_1788215708038_origin.jpg"}'
```

## 一、图搜人

### 1. 人员检测

#### POST /vlm-application/search/detectPersons
同步接口，检测图片中的行人并返回边界框坐标。

##### 请求体

```json
{
    "image_url": "http://xxx/query.jpg"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `image_url` | string | 是 | 查询图片 URL（HTTP 可访问） |

##### 返回值

**成功 (200)**
```json
{
    "code": 200,
    "message": "成功",
    "data": {
        "status": "success",
        "message": "检测到 2 个人",
        "detected_persons": [
            {
                "bbox": [
                    {"x": 550, "y": 198},
                    {"x": 786, "y": 198},
                    {"x": 786, "y": 667},
                    {"x": 550, "y": 667}
                ],
                "confidence": 0.95,
                "class_id": 0
            }
        ],
        "image_shape": [1080, 1920]
    }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `detected_persons` | array | 检测到的人员列表 |
| `detected_persons[].bbox` | array | 4 点定位多边形 `[{"x":int,"y":int},...]` |
| `detected_persons[].confidence` | float | 检测置信度 |
| `detected_persons[].class_id` | int | 类别 ID（0 代表人） |
| `image_shape` | array | 图片尺寸 `[height, width]` |

**未检测到人 (200)**
```json
{
    "code": 200,
    "message": "成功",
    "data": {
        "status": "error",
        "message": "未检测到人，请重新上传"
    }
}
```

---

### 2. 图搜人搜索（简版）

#### POST /vlm-application/search/searchPersonBrief

异步接口，提交搜索任务到 Celery 队列，返回 `task_id` 用于后续查询。**结果只返回 ES 定位信息（索引名 + 文档 ID + 相似度）**，调用方按需自行取文档详情。

##### 请求体

```json
{
    "image_url": "http://xxx/query.jpg",
    "bbox": [
        {"x": 550, "y": 198},
        {"x": 786, "y": 198},
        {"x": 786, "y": 667},
        {"x": 550, "y": 667}
    ],
    "search_method": "reid",
    "start_time": "2024-12-12 07:51:15",
    "end_time": "2026-12-12 08:50:17",
    "similarity_threshold": 0.6,
    "top_k": 10
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `image_url` | string | 是 | 查询图片 URL（HTTP 可访问） |
| `bbox` | array | 否 | 4 点定位多边形 `[{"x":int,"y":int},...]`。不传则对整图搜索，传则搜索裁剪区域 |
| `search_method` | string | 否 | 搜索方法，`"reid"` 或 `"vlm"`，默认 `"reid"`（团结湖环境仅支持 reid） |
| `start_time` | string | 否 | 开始时间过滤 `"YYYY-MM-DD HH:MM:SS"` |
| `end_time` | string | 否 | 结束时间过滤 `"YYYY-MM-DD HH:MM:SS"` |
| `similarity_threshold` | float | 否 | 余弦相似度阈值，默认 `0.6` |
| `top_k` | int | 否 | 返回的最大结果数，默认 `10` |

##### 返回值

**成功 (200)**
```json
{
    "code": 200,
    "message": "成功",
    "data": {
        "status": "success",
        "message": "任务已提交",
        "task_id": "550e8400-e29b-41d4-a716-446655440000"
    }
}
```

---

### 3. 图搜人搜索（详版）

#### POST /vlm-application/search/searchPersonFull

异步接口，入参与 `searchPersonBrief` **完全一致**（请求体、参数表同上），区别在结果：**返回命中的 ES 全量文档**（服务端按 es_id 逐条查 ES，组装 `similar_persons` 数组返回，含相似度）。

##### 返回值

**成功 (200)**：同上，返回 `task_id`。

---

### 4. 查询搜索结果

#### GET /vlm-application/search/searchPersonResult/{task_id}

同步接口，轮询 Celery 任务状态。`searchPersonBrief` 与 `searchPersonFull` 提交的任务**共用本接口**，返回结构由提交时的模式决定。

##### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | string | 是 | URL 路径参数 |

##### 返回值

**任务完成（简版任务）(200)**
```json
{
    "code": 200,
    "message": "成功",
    "data": {
        "status": "success",
        "message": "找到 3 个相似人员",
        "data": {
            "index_name": "search_person_info",
            "es_ids": ["id1", "id2", "id3"],
            "similarity_scores": [0.92, 0.87, 0.81]
        }
    }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.data.index_name` | string | 命中目标所在的 ES 索引名，多个用逗号分隔 |
| `data.data.es_ids` | array | 命中目标的 ES 文档 ID 数组，去重保序 |
| `data.data.similarity_scores` | array | 相似度数组（余弦，越大越相似），与 `es_ids` 按下标一一对应 |

**任务完成（详版任务）(200)**
```json
{
    "code": 200,
    "message": "成功",
    "data": {
        "status": "success",
        "message": "任务完成",
        "data": {
            "status": "success",
            "message": "找到 3 个相似人员",
            "processed_bboxes": [[{"x": 550, "y": 198}, {"x": 786, "y": 198}, {"x": 786, "y": 667}, {"x": 550, "y": 667}]],
            "search_method": "reid",
            "similar_persons": [
                {
                    "es_doc_id": "...",
                    "similarity_score": 0.85,
                    "camera_id": "...",
                    "image_url": "...",
                    "...": "ES 文档其余全部字段"
                }
            ]
        }
    }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.data.similar_persons` | array | 命中人员列表，每项 = ES 文档全字段 + `es_doc_id` + `similarity_score`（余弦，越大越相似） |

> 去重说明：简版 `es_ids` 去重保序（同一 es_id 多次命中取首次分数）；详版不去重（多 bbox 各自命中均列出）。

**任务处理中 (200)**
```json
{
    "code": 200,
    "message": "成功",
    "data": {
        "status": "started",
        "message": "任务正在处理中",
        "data": null
    }
}
```

**任务排队中 (200)**
```json
{
    "code": 200,
    "message": "成功",
    "data": {
        "status": "pending",
        "message": "任务正在排队中",
        "data": null
    }
}
```

**任务失败 (200)**
```json
{
    "code": 200,
    "message": "成功",
    "data": {
        "status": "error",
        "message": "任务执行失败: ...",
        "data": null
    }
}
```

---

### 已下线接口

以下接口自 2026-09 起下线（暂无调用方使用），访问返回 404：

- `POST /search/detectPersonsWithId` —— 人员检测（带 ID 缓存）
- `GET /search/getPersonBbox/{person_id}` —— 按 ID 查询 bbox（依赖上一接口的缓存）

---

### 调用流程

```
步骤一：detectPersons（同步）→ 获取人体 bbox
步骤二：searchPersonBrief（简版）或 searchPersonFull（详版）（异步）→ 提交搜索，返回 task_id
步骤三：searchPersonResult/{task_id}（轮询，间隔 1-2 秒），返回结构由步骤二选择的模式决定
```

---

## 二、步态识别

### 1. 步态特征提取入库

#### POST /vlm-application/gait/gaitFeaExtraAndIns

异步接口，从视频中提取人员步态特征向量并写入 Milvus（`gait_features` 集合），供后续 `gaitFeaCompare` 比对。

##### 请求体

```json
{
    "id": "1f63f7a20cdb4488b0c997ad1daa54b7",
    "image_url": "http://xxx/query_image.jpg",
    "video_url": "http://xxx/video.mp4",
    "is_walking": true,
    "is_full_body": true,
    "position": [
        {"x": 1119, "y": 569},
        {"x": 1344, "y": 569},
        {"x": 1344, "y": 1005},
        {"x": 1119, "y": 1005}
    ],
    "frame_interval": 4,
    "min_gait_frames": 5
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 人员 ID（与 ES 文档 ID 对应） |
| `image_url` | string | 是 | 人员查询图片 URL |
| `video_url` | string | 是 | 人员行走视频 URL |
| `is_walking` | bool | 是 | 是否行走，`false` 返回 400 |
| `is_full_body` | bool | 是 | 是否全身可见，`false` 返回 400 |
| `position` | array | 是 | 人员检测框，4 点定位多边形 |
| `frame_interval` | int | 否 | 视频抽帧间隔，默认 `4` |
| `min_gait_frames` | int | 否 | 最小步态帧数，默认 `5` |

##### 返回值

**成功 (200)**
```json
{
    "code": 200,
    "message": "成功",
    "data": {
        "task_id": "550e8400-e29b-41d4-a716-446655440000"
    }
}
```

> 说明：
> - 接口收到请求后先将 ES 文档 `has_gait` 置为 `false`（全覆盖标记），异步任务提取成功后再更新为 `true`
> - 任务结果无独立查询接口，入库结果通过 ES 文档 `has_gait` 字段体现，比对能力通过 `gaitFeaCompare` 体现
> - 仅支持行走且全身可见的视频，抽帧不足 `min_gait_frames` 时任务失败
> - Milvus `gait_features` 集合由入库侧统一建库（本服务不再自动初始化），schema：
>   `id` VARCHAR(50) 主键（=人员 ES 文档 ID）、`embedding` FLOAT_VECTOR **dim=3840**，
>   索引 AUTOINDEX、metric **COSINE**

---

### 2. 步态特征比对

#### POST /vlm-application/gait/gaitFeaCompare

同步接口，传入多个人员列表，返回步态距离 < 4.0 的相似人员 ID。

##### 请求体（JSON 数组）

```json
[
    {"id": "person_001", "isWalking": true},
    {"id": "person_002", "isWalking": true},
    {"id": "person_003", "isWalking": true}
]
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 人员 ID |
| `isWalking` | bool | 是 | 是否行走，`true` 参与比对 |

> **比对规则**：列表中的**第一个人为基准**，后续每人分别与之计算步态特征 L2 距离。距离 < 4.0 的判定为相似，加入 `similar_ids`。基准自身不在结果中。调整数组顺序可更换基准。

##### 返回值

**匹配成功 (200)**
```json
{
    "code": 200,
    "data": {
        "similar_ids": ["person_002", "person_003"]
    }
}
```

**未找到相似人员 (400)**
```json
{
    "msg": "未找到相似人员"
}
```

**请求体非数组 (400)**
```json
{
    "msg": "请求体必须为 JSON 数组"
}
```
