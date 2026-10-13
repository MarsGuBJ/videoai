import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { appModules } from "../modules/index.ts";
import { resolveAppBase } from "../utils/appBase.ts";

// 路由表由模块装配结果生成：全量模式与改造前逐条一致；
// 子包模式仅含本模块路由，/ 与兜底都指向子包默认路由。
export function createAppRouter() {
  const routes: RouteRecordRaw[] = [
    { path: "/", redirect: appModules.defaultRoute },
    ...appModules.routes,
    { path: "/:pathMatch(.*)*", redirect: "/" }
  ];
  return createRouter({
    // 相对构建（base './'）下按运行时模块地址解析部署基路径，IP/域名/子路径挂载均可路由
    history: createWebHistory(resolveAppBase()),
    routes
  });
}

// 当前构建的默认路由名（App.vue setRoute 跨模块跳转回退用；
// defaultRoute 存的是路径如 "/home"，push({ name }) 需要去掉前导斜杠）
export const APP_DEFAULT_ROUTE = appModules.defaultRoute.replace(/^\//, "");

export const router = createAppRouter();

export default router;
