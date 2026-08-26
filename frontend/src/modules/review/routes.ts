import type { RouteRecordRaw } from "vue-router";

// 万物核模块路由。页面文件保持在 ../../pages 原位，仅做逻辑分组；
// 保持现有懒加载风格，路由 name/path 与全量应用逐条一致。
export const routes: RouteRecordRaw[] = [
  { path: "/reviewTasks", name: "reviewTasks", component: () => import("../../pages/ReviewTasksPage.vue") },
  { path: "/reviewTypes", name: "reviewTypes", component: () => import("../../pages/ReviewTypesPage.vue") }
];
