// Shell 模块菜单与路由名片段（仅全量应用使用；从 store/index.ts 原样切出，文案一字不改）
export const overviewNavItem = { key: "overview", label: "总览", icon: "\uf0e4" };

export const eventsNavGroup = {
  title: "视觉事件", icon: "\uf06a", items: [
    { key: "events", label: "事件列表", icon: "\uf0f3" },
    { key: "stats", label: "事件统计", icon: "\uf080" }
  ]
};

export const configNavItems = [
  { key: "modelConfig", label: "大模型配置", icon: "\uf1c0" },
  { key: "eventConfig", label: "事件配置", icon: "\uf0ad" },
  { key: "resource", label: "资源监控", icon: "\uf233" }
];

// 「基础配置」顶级分组外壳；items 由装配工厂按模式填入（全量：视频管理子组 + 3 项；
// media 子包：仅视频管理子组，保留「基础配置 > 视频管理」层级外观）。
export function baseConfigNavGroup(items: any[]) {
  return { title: "基础配置", icon: "\uf013", items };
}

// routeNames 拆两段：overview 在全量映射中排第一，其余排在四个业务模块之后，
// 与改造前 store.routeNames 的键序逐条一致。
export const overviewRouteNames = {
  overview: "总览"
};

export const routeNames = {
  events: "事件列表",
  eventDetail: "事件详情",
  stats: "事件统计",
  eventConfig: "事件配置",
  eventConfigInfo: "事件信息配置",
  eventConfigDedup: "事件去重配置",
  eventConfigSubscriptions: "消息订阅配置",
  modelConfig: "大模型配置",
  resource: "资源监控",
  logs: "日志管理",
  permissions: "权限中心"
};
