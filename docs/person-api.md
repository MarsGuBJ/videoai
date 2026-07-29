# 接口规范

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

### 2. 图搜人搜索

#### POST /vlm-application/search/searchPersonByBbox

异步接口，提交搜索任务到 Celery 队列，返回 `task_id` 用于后续查询。

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
| `search_method` | string | 否 | 搜索方法，`"reid"` 或 `"vlm"`，默认 `"reid"` |
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

### 3. 查询搜索结果

#### GET /vlm-application/search/searchPersonResult/{task_id}

同步接口，轮询 Celery 任务状态。

##### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | string | 是 | URL 路径参数 |

##### 返回值

**任务完成 (200)**
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
            "processed_bboxes": [[{"x":..., "y":...}, ...]],
            "search_method": "vlm",
            "similar_persons": [
                {
                    "es_doc_id": "...",
                    "similarity_score": 0.85,
                    "create_time": 1735708249,
                    "camera_id": "...",
                    "image_url": "..."
                }
            ]
        }
    }
}
```

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

### 4. 人员检测（带唯一 ID）

#### POST /vlm-application/search/detectPersonsWithId

同步接口，检测图片中的行人，为每个行人分配全局唯一 UUID（`person_id`），并自动写入 2 小时 TTL 缓存。后续可通过 `getPersonBboxById` 按 ID 查询。

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
                "person_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
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
| `detected_persons[].person_id` | string | UUID v4，全局唯一，供后续按 ID 查询 |
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

### 5. 按 ID 查询人员 bbox

#### GET /vlm-application/search/getPersonBbox/{person_id}

从 TTL 缓存中查询 detectPersonsWithId 接口检测到的人员信息。缓存 2 小时过期，超时需重新调用 detectPersonsWithId。

##### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `person_id` | string | 是 | URL 路径参数，detectPersonsWithId 分配的 UUID |

##### 返回值

**成功 (200)**
```json
{
    "code": 200,
    "message": "成功",
    "data": {
        "person_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "bbox": [
            {"x": 550, "y": 198},
            {"x": 786, "y": 198},
            {"x": 786, "y": 667},
            {"x": 550, "y": 667}
        ],
        "confidence": 0.95,
        "image_url": "http://xxx/query.jpg"
    }
}
```

**未找到 (200)**
```json
{
    "code": 200,
    "message": "成功",
    "data": null,
    "status": false,
    "message": "未找到该 person_id 或已过期"
}
```

---

### 调用流程

```
步骤一：detectPerson（同步）→ 获取人体 bbox
步骤二：searchPersonByBbox（异步）→ 提交搜索，返回 task_id
步骤三：searchPersonResult/{task_id}（轮询，间隔 1-2 秒）
```

---

## 二、步态识别

### 步态特征比对

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
