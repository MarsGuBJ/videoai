import type { RouteRecordRaw } from "vue-router";

// 万物搜模块路由。页面文件保持在 ../../pages 原位，仅做逻辑分组；
// 保持现有懒加载风格，路由 name/path 与全量应用逐条一致。
export const routes: RouteRecordRaw[] = [
  { path: "/home", name: "home", component: () => import("../../pages/HomePage.vue") },
  { path: "/exact", name: "exact", component: () => import("../../pages/ExactSearchPage.vue") },
  { path: "/localVideo", name: "localVideo", component: () => import("../../pages/LocalVideoPage.vue") },
  { path: "/textImage", name: "textImage", component: () => import("../../pages/TextImagePage.vue") },
  { path: "/imageSearch", name: "imageSearch", component: () => import("../../pages/ImageSearchPage.vue") },
  { path: "/quickDeploy", name: "quickDeploy", component: () => import("../../pages/QuickDeployPage.vue") },
  { path: "/track", name: "track", component: () => import("../../pages/TrackPage.vue") },
  { path: "/monitorSearch", name: "monitorSearch", component: () => import("../../pages/MonitorSearchPage.vue") }
];
