import type { RouteRecordRaw } from "vue-router";

// 算法布控模块路由。页面文件保持在 ../../pages 原位，仅做逻辑分组；
// 保持现有懒加载风格，路由 name/path 与全量应用逐条一致。
export const routes: RouteRecordRaw[] = [
  { path: "/algorithms", name: "algorithms", component: () => import("../../pages/AlgorithmsPage.vue") },
  { path: "/versionManager", name: "versionManager", component: () => import("../../pages/VersionManagerPage.vue") },
  { path: "/versionDetail", name: "versionDetail", component: () => import("../../pages/VersionDetailPage.vue") },
  { path: "/previewFile", name: "previewFile", component: () => import("../../pages/PreviewFilePage.vue") },
  { path: "/deployTasks", name: "deployTasks", component: () => import("../../pages/DeployTasksPage.vue") },
  { path: "/deployTaskDetail", name: "deployTaskDetail", component: () => import("../../pages/DeployTaskDetailPage.vue") },
  { path: "/events", name: "events", component: () => import("../../pages/EventsPage.vue") },
  { path: "/eventDetail", name: "eventDetail", component: () => import("../../pages/EventDetailPage.vue") }
];
