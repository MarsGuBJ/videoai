import { reactive } from "vue";
import { appModules } from "../modules/index.ts";

const img = {
  target: "/prototype/target.jpg",
  mountain: "/prototype/mountain.jpg",
  map: "/prototype/map.jpg",
  portrait: "/prototype/portrait.jpg",
  analyst: "/prototype/analyst.jpg",
  targetBoard: "/prototype/targetBoard.jpg",
  car: "/prototype/car.jpg",
  ai: "/prototype/ai.jpg"
};

export const store = reactive({
      img,
      lastLocalVideo: null,
      accessConfig: {
        gb28181: {
          enabled: true,
          sipId: "34020000002000000001",
          sipDomain: "3402000000",
          sipIp: "192.168.11.195",
          sipPort: "15060",
          password: "",
          parentPort: "15061",
          receivePortStart: "30000",
          receivePortEnd: "30500"
        },
        ga1400: {
          enabled: true,
          platformId: "44020000005030000112",
          platformIp: "192.168.11.195",
          port: "1400",
          password: "Aa123456",
          resourcePath: "./data",
          autoRegister: true
        },
        certificates: []
      },
      // 菜单与路由名由模块装配结果生成；全量模式（默认）与改造前硬编码逐条一致
      navGroups: appModules.navGroups,
      routeNames: appModules.routeNames,
      entryCards: [
        { route: "exact", icon: "⌕", title: "文搜视频", desc: "通过文字描述快速检索视频内容，精准定位目标片段" },
        { route: "textImage", icon: "▧", title: "文搜图", desc: "用文字描述搜索海量图片库，快速找到匹配的图像资源" },
        { route: "imageSearch", icon: "▣", title: "图搜图", desc: "以上传图片为参考，在数据库中查找相似图像内容" },
        { route: "localVideo", icon: "▤", title: "视频分析", desc: "上传本地视频文件，自动提取关键帧、目标、事件与时间线" }
      ],
      results: [
        { title: "南门入口-目标出现", date: "2026-07-12 08:30:12", location: "园区南门入口", score: 98, type: "视频片段", image: img.car, desc: "检测到疑似目标车辆进入园区，方向由南向北。" },
        { title: "停车场-相似车辆", date: "2026-07-12 08:35:45", location: "A座停车区", score: 95, type: "图像结果", image: img.target, desc: "目标在停车区域短暂停留，与查询特征高度相似。" },
        { title: "生产A区-人员同行", date: "2026-07-12 08:38:20", location: "生产A区通道", score: 87, type: "视频片段", image: img.mountain, desc: "目标附近出现同行人员，可进一步查看上下文。" },
        { title: "办公区-访客匹配", date: "2026-07-12 08:42:18", location: "办公区一层", score: 82, type: "图像结果", image: img.portrait, desc: "访客图像与上传目标特征匹配，建议复核。" },
        { title: "西门岗亭-目标离开", date: "2026-07-12 09:10:03", location: "园区西门", score: 76, type: "视频片段", image: img.analyst, desc: "目标离开园区，轨迹链路已形成闭环。" },
        { title: "道路卡口-车辆二次出现", date: "2026-07-12 09:18:25", location: "外环路卡口", score: 72, type: "图像结果", image: img.targetBoard, desc: "外部卡口捕获疑似车辆，可生成布控任务。" },
        { title: "仓储区-低相似结果", date: "2026-07-12 09:31:06", location: "仓储区入口", score: 68, type: "图像结果", image: img.ai, desc: "低相似度结果，仅供人工复核参考。" },
        { title: "北门出口-模糊匹配", date: "2026-07-12 09:36:44", location: "园区北门出口", score: 63, type: "视频片段", image: img.map, desc: "画面模糊，建议结合时间范围继续过滤。" }
      ],
      reviewTasks: [
        { id: "WH-20260712-001", title: "南门入口白色车辆复核", type: "目标识别复核", source: "万物搜/文搜视频", status: "待复核", priority: "高", owner: "徐妍", date: "2026-07-12 09:42", image: img.car, resultIndex: 0, ai: "AI 判断该车辆与查询目标相似度 98%，建议人工确认是否为同一目标。", desc: "复核南门入口和停车场两段视频，确认白色车辆是否连续出现。" },
        { id: "WH-20260712-002", title: "停车场相似车辆确认", type: "车辆相似复核", source: "图搜图", status: "复核中", priority: "高", owner: "李牧", date: "2026-07-12 10:08", image: img.target, resultIndex: 1, ai: "目标在 A 座停车区域短暂停留，车头特征与参考图高度一致。", desc: "需要确认车牌遮挡情况下是否可进入布控任务。" },
        { id: "WH-20260712-003", title: "访客身份匹配复核", type: "人员身份复核", source: "文搜图", status: "待复核", priority: "中", owner: "未分配", date: "2026-07-12 10:26", image: img.portrait, resultIndex: 3, ai: "访客图像与上传目标特征匹配，相似度 82%，建议结合登记记录复核。", desc: "核对访客进入办公区的时间、同行人员和登记信息。" }
      ],
      prototypeTaskRows: [
        { id: "#TM-2847", type: "人员入侵检测", created: "2026-01-15 14:32:08", timeValid: "有效", status: "已完成", location: "B6-屋顶-货梯侧楼梯", confidence: "high", executionStatus: "已完成", duration: "6秒", reason: "视频中出现的人员为保洁人员，身穿灰色保洁马甲、手持拖把，符合保洁人员特征，属于应过滤的非入侵人员。", evidence: "视频09:23:28-09:23:40显示一名穿灰色马甲、持拖把的女性从楼梯走下，符合保洁人员特征。", image: img.car },
        { id: "#TM-2846", type: "车辆违停识别", created: "2026-01-15 13:14:17", timeValid: "无效", status: "进行中", location: "A座停车区", confidence: "high", executionStatus: "已完成", duration: "8秒", reason: "目标车辆停留时间较短，当前判定为非违停。", evidence: "停车区域画面显示车辆短暂停靠后驶离，未满足违停时长条件。", image: img.target },
        { id: "#TM-2845", type: "烟火检测告警", created: "2026-01-15 11:48:36", timeValid: "无效", status: "待处理", location: "仓储区入口", confidence: "medium", executionStatus: "已完成", duration: "5秒", reason: "画面中的亮点更接近反光或灯光，暂未确认烟火事件。", evidence: "关键帧未发现持续烟雾或明火特征，建议人工复核。", image: img.ai },
        { id: "#TM-2844", type: "安全帽佩戴检测", created: "2026-01-15 10:22:21", timeValid: "无效", status: "已完成", location: "生产A区通道", confidence: "high", executionStatus: "已完成", duration: "7秒", reason: "人员已佩戴安全帽，告警属于误报。", evidence: "连续关键帧均可见安全帽轮廓，未发现脱帽状态。", image: img.mountain },
        { id: "#TM-2843", type: "区域入侵检测", created: "2026-01-15 09:15:12", timeValid: "无效", status: "已完成", location: "园区南门入口", confidence: "high", executionStatus: "已完成", duration: "6秒", reason: "目标位于授权通行区域，未形成有效入侵事件。", evidence: "目标从入口正常通行，未越过禁入区域边界。", image: img.map }
      ],
      // 事件信息配置条目：事件信息配置页维护，复核类型弹窗“算法名称”下拉复用
      eventInfoRows: [
        { name: "家禽检测", code: "FOWL_DETECTION", level: "低", category: "待完成", order: 25, enabled: true },
        { name: "区域入侵", code: "INTRUSION_DEC", level: "低", category: "安防事件", order: 24, enabled: true },
        { name: "烟火识别", code: "SMOKE", level: "低", category: "消防事件", order: 23, enabled: true },
        { name: "RK_周界入侵", code: "RK_INTRUSION_DEC", level: "高", category: "安防事件", order: 22, enabled: true },
        { name: "污水应急监控", code: "PERSON_WADE", level: "低", category: "环境事件", order: 21, enabled: true },
        { name: "睡岗", code: "SLEEP", level: "低", category: "行为事件", order: 20, enabled: true },
        { name: "离岗", code: "LEAVE", level: "低", category: "行为事件", order: 19, enabled: true },
        { name: "RK_抽烟", code: "RK_SMOKING", level: "中", category: "行为事件", order: 18, enabled: true },
        { name: "RK_物品占用通道", code: "RK_OCCUPIED_AREA", level: "低", category: "安防事件", order: 17, enabled: true },
        { name: "非机动车识别", code: "NONVEHICLE", level: "低", category: "交通事件", order: 14, enabled: true }
      ],
      algorithmRows: [
        { id: 1, name: "抽烟", code: "SMOKING", prompt: "你是园区安防监控事件复检助手，请判断画面中是否存在抽烟行为。", remark: "抽烟", fields: "识别对象", updated: "2026-04-27 10:05:40" },
        { id: 2, name: "垃圾识别", code: "RUBBISH", prompt: "你是园区安防监控事件复检助手，请识别画面中是否存在垃圾堆放。", remark: "-", fields: "-", updated: "2026-04-13 16:21:10" },
        { id: 3, name: "车辆违停", code: "PARKING", prompt: "你是园区安防监控事件复检助手，请判断车辆是否违规停放。", remark: "-", fields: "-", updated: "2026-04-10 14:31:29" },
        { id: 4, name: "人员入侵", code: "PERSON_INTRUSION", prompt: "你是园区安防监控事件复检助手，请判断是否有人员进入禁入区域。", remark: "过滤保安、保洁、施工", fields: "识别对象", updated: "2026-04-24 17:06:32" },
        { id: 7, name: "电动车识别", code: "EBIKE_DETECTION", prompt: "你是园区安防监控事件复检助手，请识别画面中的电动车目标。", remark: "-", fields: "-", updated: "2026-04-10 16:32:45" },
        { id: 9, name: "烟火监测", code: "SMOKE_FIRE_DETECTION", prompt: "你是园区安防监控事件复检助手，请判断是否出现烟雾或明火。", remark: "-", fields: "识别对象", updated: "2026-04-27 16:08:33" }
      ],
      algorithmManageRows: [
        { id: "ALG-001", name: "人员入侵检测", code: "PERSON_INTRUSION", scene: "园区周界", version: "v2.3.1", status: "运行中", owner: "算法组", updated: "2026-04-24 17:06:32", versions: 3 },
        { id: "ALG-002", name: "车辆违停识别", code: "PARKING", scene: "停车场/道路", version: "v1.8.0", status: "运行中", owner: "算法组", updated: "2026-04-10 14:31:29", versions: 2 },
        { id: "ALG-003", name: "烟火检测告警", code: "SMOKE_FIRE_DETECTION", scene: "仓储/楼宇", version: "v3.0.2", status: "待发布", owner: "模型运营", updated: "2026-04-27 16:08:33", versions: 4 },
        { id: "ALG-004", name: "电动车识别", code: "EBIKE_DETECTION", scene: "楼宇入口", version: "v1.2.4", status: "已停用", owner: "安防中心", updated: "2026-04-10 16:32:45", versions: 1 }
      ],
      versionRows: [
        { id: "VER-2847", algorithm: "人员入侵检测", version: "v2.3.1", name: "周界场景优化版", status: "已发布", file: "person_intrusion_v231.zip", creator: "徐妍", created: "2026-04-24 17:06:32", desc: "优化夜间低照度场景下的人员入侵识别效果。" },
        { id: "VER-2846", algorithm: "车辆违停识别", version: "v1.8.0", name: "停车场增强版", status: "已发布", file: "parking_v180.zip", creator: "李牧", created: "2026-04-10 14:31:29", desc: "提升车位线遮挡、临停车辆的识别稳定性。" },
        { id: "VER-2845", algorithm: "烟火检测告警", version: "v3.0.2", name: "烟火复核测试版", status: "待发布", file: "smoke_fire_v302.zip", creator: "王珂", created: "2026-04-27 16:08:33", desc: "新增烟雾与明火混合场景判断提示词。" },
        { id: "VER-2844", algorithm: "电动车识别", version: "v1.2.4", name: "楼宇入口识别版", status: "测试中", file: "ebike_detection_v124.zip", creator: "赵一鸣", created: "2026-04-10 16:32:45", desc: "用于识别电动车进入楼宇大厅等风险行为。" }
      ],
      deployTaskRows: [
        { id: "BK-20260716-001", name: "南门人员入侵布控", algorithm: "人员入侵检测", area: "园区南门", points: "南门入口、访客通道", time: "全天", threshold: 85, status: "运行中", alerts: 12, owner: "徐妍", created: "2026-07-16 09:18", desc: "针对南门禁入区域进行人员入侵实时布控，触发后推送至安防中心。" },
        { id: "BK-20260716-002", name: "A座停车场违停布控", algorithm: "车辆违停识别", area: "A座停车区", points: "A1停车场、A2停车场", time: "工作日 08:00-20:00", threshold: 80, status: "运行中", alerts: 8, owner: "李牧", created: "2026-07-16 10:25", desc: "识别停车场通道、消防通道内的车辆违停行为。" },
        { id: "BK-20260715-006", name: "仓储区烟火告警", algorithm: "烟火检测告警", area: "仓储区", points: "仓储一区、装卸口", time: "全天", threshold: 90, status: "已停止", alerts: 0, owner: "王珂", created: "2026-07-15 17:40", desc: "仓储区烟雾、明火异常识别，支持平台弹窗和消息推送。" },
        { id: "BK-20260714-011", name: "北门电动车识别", algorithm: "电动车识别", area: "园区北门", points: "北门入口、楼宇大厅", time: "07:00-22:00", threshold: 75, status: "已停止", alerts: 21, owner: "赵一鸣", created: "2026-07-14 14:06", desc: "识别电动车进入楼宇大厅等风险行为，当前因点位调整暂停。" }
      ],
      eventRows: [
        { id: "EV-20260716-0001", name: "南门人员入侵告警", type: "人员入侵", level: "高", eventSource: "中心推理平台", area: "园区南门", point: "南门入口", status: "待复核", time: "2026-07-16 14:32:08", owner: "徐妍", image: img.portrait, desc: "检测到非授权人员进入南门禁入区域，已触发平台告警。" },
        { id: "EV-20260716-0002", name: "A座停车场车辆违停", type: "车辆违停", level: "中", eventSource: "云边协同平台", area: "A座停车区", point: "A1停车场", status: "有效", time: "2026-07-16 13:14:17", owner: "李牧", image: img.car, desc: "车辆停放在消防通道附近，已分派现场人员确认。" },
        { id: "EV-20260716-0003", name: "仓储区疑似烟火", type: "烟火检测", level: "高", eventSource: "中心推理平台", area: "仓储区", point: "装卸口", status: "待复核", time: "2026-07-16 11:48:36", owner: "王珂", image: img.ai, desc: "画面中出现疑似烟雾，需要人工复核确认是否为真实火情。" },
        { id: "EV-20260716-0004", name: "北门电动车进入大厅", type: "电动车识别", level: "中", eventSource: "中心推理平台", area: "园区北门", point: "楼宇大厅", status: "待复核", time: "2026-07-16 10:22:21", owner: "赵一鸣", image: img.targetBoard, desc: "检测到电动车进入楼宇大厅，已通知现场人员处理。" },
        { id: "EV-20260716-0005", name: "周界夜间入侵", type: "周界入侵", level: "高", eventSource: "云边协同平台", area: "园区周界", point: "东侧围栏", status: "有效", time: "2026-07-16 09:15:12", owner: "安防中心", image: img.mountain, desc: "夜间周界出现移动目标，经复核为巡检人员，事件关闭。" },
        { id: "EV-20260715-0021", name: "垃圾堆放识别", type: "垃圾识别", level: "低", eventSource: "云边协同平台", area: "办公区", point: "办公区一层", status: "有效", time: "2026-07-15 16:20:44", owner: "物业中心", image: img.map, desc: "办公区公共区域检测到垃圾堆放，已完成清理。" }
      ],
      eventTrend: [
        { label: "07-10", value: 18 },
        { label: "07-11", value: 24 },
        { label: "07-12", value: 31 },
        { label: "07-13", value: 22 },
        { label: "07-14", value: 36 },
        { label: "07-15", value: 29 },
        { label: "07-16", value: 42 }
      ],
      eventTypeStats: [
        { label: "人员入侵", value: 34 },
        { label: "车辆违停", value: 28 },
        { label: "烟火检测", value: 16 },
        { label: "电动车识别", value: 13 },
        { label: "周界入侵", value: 9 }
      ],
      eventSourceRows: [
        { name: "云边协同平台 - 边缘算法", url: "api.edge-cloud.com/v1/alerts", types: "人员入侵、车辆检测", frequency: "每5分钟", status: "运行中", lastSync: "2024-01-15 14:30", mode: "主动拉取", owner: "边缘平台" },
        { name: "中心端布控算法平台", url: "center-control.gov.cn/api/events", types: "烟火检测、安全帽", frequency: "实时推送", status: "运行中", lastSync: "2024-01-15 14:32", mode: "被动接收", owner: "算法平台" },
        { name: "下游业务系统A", url: "business-system-a.com/webhook", types: "区域入侵", frequency: "每10分钟", status: "暂停", lastSync: "2024-01-15 12:00", mode: "主动拉取", owner: "业务系统A" },
        { name: "视频事件平台", url: "video-event.platform.cn/api", types: "跌倒检测、聚集检测", frequency: "实时推送", status: "运行中", lastSync: "2024-01-15 14:31", mode: "被动接收", owner: "视频平台" },
        { name: "第三方告警服务", url: "third-party-alerts.io/v2", types: "设备异常", frequency: "每30分钟", status: "连接失败", lastSync: "2024-01-15 10:00", mode: "主动拉取", owner: "第三方服务" }
      ],
      resourceRows: [
        { ip: "192.168.1.100", mn: "MN24010001", status: "在线", updated: "2024-01-18 15:30:45", gpus: [
          { name: "NVIDIA A100 GPU-0", status: "繁忙", compute: 75, memory: 50, memoryText: "40GB/80GB", temperature: "65°C", power: "57.4w" },
          { name: "NVIDIA A100 GPU-1", status: "空闲", compute: 45, memory: 44, memoryText: "35GB/80GB", temperature: "62°C", power: "57.3w" }
        ] },
        { ip: "192.168.1.101", mn: "MN24010002", status: "在线", updated: "2024-01-18 15:29:18", gpus: [
          { name: "NVIDIA A100 GPU-0", status: "繁忙", compute: 82, memory: 63, memoryText: "50GB/80GB", temperature: "69°C", power: "61.8w" },
          { name: "NVIDIA A100 GPU-1", status: "繁忙", compute: 78, memory: 58, memoryText: "46GB/80GB", temperature: "67°C", power: "59.1w" }
        ] },
        { ip: "192.168.1.102", mn: "MN24010003", status: "在线", updated: "2024-01-18 15:28:52", gpus: [
          { name: "NVIDIA A40 GPU-0", status: "繁忙", compute: 68, memory: 52, memoryText: "25GB/48GB", temperature: "59°C", power: "46.8w" },
          { name: "NVIDIA A40 GPU-1", status: "空闲", compute: 18, memory: 27, memoryText: "13GB/48GB", temperature: "49°C", power: "38.2w" }
        ] },
        { ip: "192.168.1.103", mn: "MN24010004", status: "离线", updated: "2024-01-18 12:10:03", gpus: [
          { name: "NVIDIA T4 GPU-0", status: "离线", compute: 0, memory: 0, memoryText: "0GB/16GB", temperature: "-", power: "-" },
          { name: "NVIDIA T4 GPU-1", status: "离线", compute: 0, memory: 0, memoryText: "0GB/16GB", temperature: "-", power: "-" }
        ] }
      ],
      logRows: [
        { time: "2026-07-17 09:42:18", user: "管理员", module: "算法管理", action: "新增算法", target: "人员入侵检测", result: "成功", ip: "10.8.12.45" },
        { time: "2026-07-17 09:36:02", user: "徐妍", module: "事件配置", action: "新增数据源", target: "视频事件平台", result: "成功", ip: "10.8.12.33" },
        { time: "2026-07-17 09:24:51", user: "李牧", module: "布控任务", action: "启停任务", target: "A座停车场违停布控", result: "成功", ip: "10.8.12.37" },
        { time: "2026-07-17 09:18:43", user: "系统", module: "大模型配置", action: "连接检测", target: "硅基流动-DeepSeek", result: "失败", ip: "127.0.0.1" },
        { time: "2026-07-17 09:12:09", user: "王珂", module: "事件列表", action: "导出事件", target: "近7日事件", result: "成功", ip: "10.8.12.41" },
        { time: "2026-07-17 08:55:26", user: "系统", module: "资源监控", action: "手动同步", target: "GPU资源池", result: "成功", ip: "127.0.0.1" }
      ],
      ruleLogRows: [
        { device: "室外-B1北侧道路2", rule: "测试图像过滤", algorithm: "车辆违停乱放", type: "实时重复图像去重", status: "执行成功", count: 1, time: "2024-09-27 15:57:34" },
        { device: "室外-B1北侧道路2", rule: "测试图像过滤", algorithm: "车辆违停乱放", type: "实时重复图像去重", status: "执行成功", count: 1, time: "2024-09-27 15:53:49" },
        { device: "室外-B1北侧道路2", rule: "测试图像过滤", algorithm: "车辆违停乱放", type: "实时重复图像去重", status: "执行失败", count: 1, time: "2024-09-27 15:46:27" },
        { device: "A1-1郡-室外#01", rule: "抽烟", algorithm: "RK_抽烟", type: "区间重复图像去重", status: "执行失败", count: 0, time: "2024-09-19 10:16:03" },
        { device: "A1-1郡-室外#01", rule: "抽烟", algorithm: "RK_抽烟", type: "时间维度去重", status: "执行成功", count: 1, time: "2024-09-19 09:41:04" },
        { device: "A1-1郡-室外#01", rule: "抽烟", algorithm: "RK_抽烟", type: "时间维度去重", status: "执行成功", count: 1, time: "2024-09-19 09:40:58" },
        { device: "A1-1郡-室外#01", rule: "抽烟", algorithm: "RK_抽烟", type: "时间维度去重", status: "执行成功", count: 1, time: "2024-09-19 09:40:53" },
        { device: "室外-B1北侧道路2", rule: "测试图像过滤", algorithm: "车辆违停乱放", type: "实时重复图像去重", status: "执行成功", count: 1, time: "2024-09-27 15:42:17" },
        { device: "室外-B1北侧道路2", rule: "测试图像过滤", algorithm: "车辆违停乱放", type: "实时重复图像去重", status: "执行成功", count: 1, time: "2024-09-27 15:40:11" },
        { device: "A1-1郡-室外#01", rule: "抽烟", algorithm: "RK_抽烟", type: "时间维度去重", status: "执行失败", count: 0, time: "2024-09-19 09:32:05" },
        { device: "A1-1郡-室外#01", rule: "抽烟", algorithm: "RK_抽烟", type: "区间重复图像去重", status: "执行成功", count: 1, time: "2024-09-19 09:28:41" }
      ],
      pushLogRows: [
        { id: 1, task: "公交车数据推送任务", result: "成功", error: "-", content: "设备状态、告警消息、点位信息", time: "2026-07-17 09:30:18" },
        { id: 2, task: "重点事件HTTP推送", result: "失败", error: "目标服务超时", content: "高等级事件、复核结论", time: "2026-07-17 08:58:41" },
        { id: 3, task: "云边协同MQ推送", result: "成功", error: "-", content: "边缘设备事件流", time: "2026-07-16 18:22:10" }
      ],
      pushPayload: `{
  "deviceId": "string",
  "deviceCode": "string",
  "deviceData": {
    "lightControlGridActivePower": {
      "id": null,
      "deviceId": "yunzhisheng89",
      "name": "灯控功率",
      "code": "lightControlGridActivePower",
      "dataType": "STRING",
      "value": {
        "value_real": "0",
        "value_format": "0",
        "value": "0"
      },
      "lastTime": "2023-02-17 16:01:19"
    }
  },
  "deviceStatus": "NORMAL",
  "warnMessages": []
}`,
      permissionRoles: [
        { id: "ROLE-001", name: "系统管理员", code: "SYSTEM_ADMIN", status: "启用", users: 1, scope: "全部数据", desc: "拥有平台全部功能和基础配置管理权限", updated: "2026-07-17 09:42" },
        { id: "ROLE-002", name: "安防运营", code: "SECURITY_OPERATOR", status: "启用", users: 2, scope: "安防中心", desc: "负责万物搜、布控任务、事件处置和日志查看", updated: "2026-07-16 18:20" },
        { id: "ROLE-003", name: "算法管理员", code: "ALGORITHM_ADMIN", status: "启用", users: 1, scope: "算法组", desc: "维护算法、版本号、大模型配置和资源监控", updated: "2026-07-15 15:08" },
        { id: "ROLE-004", name: "复核专员", code: "REVIEWER", status: "启用", users: 1, scope: "万物核", desc: "处理人工复核任务和复核类型配置", updated: "2026-07-14 11:36" },
        { id: "ROLE-005", name: "访客演示", code: "DEMO_GUEST", status: "停用", users: 1, scope: "只读演示", desc: "客户演示场景下的只读账号权限", updated: "2026-07-12 10:11" }
      ],
      permissionTree: [
        { group: "万物搜", items: ["万物搜主页", "文搜视频", "轨迹寻踪", "图搜图", "快速布防"] },
        { group: "万物核", items: ["任务管理", "复核类型管理", "新建复核类型", "复核结果导出"] },
        { group: "算法布控", items: ["布控任务", "算法管理", "版本号管理", "新增算法", "新增版本号"] },
        { group: "视觉事件", items: ["事件列表", "事件统计", "事件详情", "事件处置"] },
        { group: "基础配置", items: ["事件配置", "大模型配置", "资源监控", "日志管理", "权限中心"] }
      ],
      permissionUsers: [
        { name: "管理员", account: "admin", dept: "平台管理部", role: "系统管理员", status: "启用" },
        { name: "徐妍", account: "xu.yan", dept: "安防中心", role: "安防运营", status: "启用" },
        { name: "李牧", account: "li.mu", dept: "安防中心", role: "安防运营", status: "启用" },
        { name: "王珂", account: "wang.ke", dept: "算法组", role: "算法管理员", status: "启用" },
        { name: "赵一鸣", account: "zhao.ym", dept: "复核中心", role: "复核专员", status: "启用" },
        { name: "演示用户", account: "demo", dept: "客户演示", role: "访客演示", status: "停用" }
      ]
    });

    export function statusClass(status) {
      if (status === "待复核" || status === "待处理" || status === "待发布" || status === "暂停") return "waiting";
      if (status === "复核中" || status === "进行中" || status === "运行中" || status === "测试中" || status === "处理中" || status === "繁忙" || status === "同步中") return "processing";
      if (status === "有效" || status === "已通过" || status === "启用" || status === "已完成" || status === "已发布" || status === "已处理" || status === "运行良好" || status === "在线" || status === "空闲" || status === "成功" || status === "执行成功") return "pass";
      if (status === "无效" || status === "未成功连接" || status === "已驳回" || status === "停用" || status === "已停用" || status === "已停止" || status === "已暂停" || status === "已结束" || status === "已关闭" || status === "连接异常" || status === "连接失败" || status === "离线" || status === "失败" || status === "执行失败") return "reject";
      return "";
    }

    export function levelClass(level) {
      if (level === "高") return "high";
      if (level === "中") return "medium";
      if (level === "低") return "low";
      return "";
    }

    export function priorityClass(priority) {
      if (priority === "高") return "high";
      if (priority === "中") return "medium";
      if (priority === "低") return "low";
      return "";
    }

    export function similarityColor(score) {
      const value = Math.min(100, Math.max(0, Number(score) || 0));
      return `hsl(${value * 1.2} 72% 38%)`;
    }

    export function isActiveNav(key, route) {
      if (key === "overview") return route === "overview";
      if (key === "media") return ["media", "cameraList", "mediaDeviceWizard", "mediaDeviceDetail", "mediaDeviceEdit"].includes(route);
      if (key === "mediaAccessConfig") return route === "mediaAccessConfig";
      if (key === "mediaCloudConfig") return route === "mediaCloudConfig";
      if (key === "mediaPreview") return route === "mediaPreview";
      if (key === "mediaPlayback") return route === "mediaPlayback";
      if (key === "mediaWall") return route === "mediaWall";
      if (key === "mediaAlarm") return route === "mediaAlarm";
      if (key === "home") return route === "home";
      if (key === "exact") return route === "exact";
      if (key === "localVideo") return route === "localVideo";
      if (key === "textImage") return route === "textImage";
      if (key === "imageSearch") return route === "imageSearch";
      if (key === "track") return route === "track";
      if (key === "quickDeploy") return route === "quickDeploy";
      if (key === "reviewTasks") return route === "reviewTasks";
      if (key === "reviewTypes") return route === "reviewTypes";
      if (key === "algorithms") return ["algorithms", "versionManager", "versionDetail", "previewFile"].includes(route);
      if (key === "deployTasks") return ["deployTasks", "deployTaskDetail"].includes(route);
      if (key === "events") return ["events", "eventDetail"].includes(route);
      if (key === "stats") return route === "stats";
      if (key === "eventConfig") return ["eventConfig", "eventConfigInfo", "eventConfigDedup", "eventConfigSubscriptions"].includes(route);
      if (key === "modelConfig") return route === "modelConfig";
      if (key === "resource") return route === "resource";
      if (key === "logs") return route === "logs";
      if (key === "permissions") return route === "permissions";
      return false;
    }
