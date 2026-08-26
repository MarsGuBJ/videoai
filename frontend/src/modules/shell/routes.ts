import type { RouteRecordRaw } from "vue-router";

// Shell 模块路由（仅全量应用使用）：总览 + 视觉事件 + 基础配置及隐藏页面。
// overview 单独导出：全量路由表中它排在最前（/ redirect 之后），
// 其余 shell 路由排在四个业务模块之后，与改造前路由表逐条一致。
export const overviewRoute: RouteRecordRaw =
  { path: "/overview", name: "overview", component: () => import("../../pages/OverviewPage.vue") };

export const routes: RouteRecordRaw[] = [
  { path: "/events", name: "events", component: () => import("../../pages/EventsPage.vue") },
  { path: "/eventDetail", name: "eventDetail", component: () => import("../../pages/EventDetailPage.vue") },
  { path: "/stats", name: "stats", component: () => import("../../pages/StatsPage.vue") },
  { path: "/eventConfig", name: "eventConfig", component: () => import("../../pages/EventConfigPage.vue") },
  { path: "/eventConfigInfo", name: "eventConfigInfo", component: () => import("../../pages/EventConfigInfoPage.vue") },
  { path: "/eventConfigDedup", name: "eventConfigDedup", component: () => import("../../pages/EventConfigDedupPage.vue") },
  { path: "/eventConfigSubscriptions", name: "eventConfigSubscriptions", component: () => import("../../pages/EventConfigSubscriptionsPage.vue") },
  { path: "/modelConfig", name: "modelConfig", component: () => import("../../pages/ModelConfigPage.vue") },
  { path: "/resource", name: "resource", component: () => import("../../pages/ResourcePage.vue") },
  { path: "/logs", name: "logs", component: () => import("../../pages/LogsPage.vue") },
  { path: "/permissions", name: "permissions", component: () => import("../../pages/PermissionsPage.vue") }
];
