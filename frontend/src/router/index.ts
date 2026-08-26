import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { appModules } from "../modules/index.ts";

// 路由表由模块装配结果生成：全量模式与改造前逐条一致；
// 子包模式仅含本模块路由，/ 与兜底都指向子包默认路由。
export function createAppRouter() {
  const routes: RouteRecordRaw[] = [
    { path: "/", redirect: appModules.defaultRoute },
    ...appModules.routes,
    { path: "/:pathMatch(.*)*", redirect: "/" }
  ];
  return createRouter({
    history: createWebHistory(),
    routes
  });
}

// 当前构建的默认路由名（App.vue setRoute 跨模块跳转回退用；
// defaultRoute 存的是路径如 "/home"，push({ name }) 需要去掉前导斜杠）
export const APP_DEFAULT_ROUTE = appModules.defaultRoute.replace(/^\//, "");

export const router = createAppRouter();

export default router;
