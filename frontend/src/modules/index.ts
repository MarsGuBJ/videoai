import type { RouteRecordRaw } from "vue-router";
import { routes as searchRoutes } from "./search/routes.ts";
import * as searchNav from "./search/nav.ts";
import { routes as mediaRoutes } from "./media/routes.ts";
import * as mediaNav from "./media/nav.ts";
import { routes as controlRoutes } from "./control/routes.ts";
import * as controlNav from "./control/nav.ts";
import { routes as reviewRoutes } from "./review/routes.ts";
import * as reviewNav from "./review/nav.ts";
import { overviewRoute, routes as shellRoutes } from "./shell/routes.ts";
import * as shellNav from "./shell/nav.ts";

// 单仓多模式装配：按 VITE_APP_MODULE 把各模块的路由/菜单/路由名拼成一套应用配置。
// 缺省或 full → 全量应用（与改造前逐条一致）；search|media|control|review → 仅该模块。

export interface ResolvedApp {
  routes: RouteRecordRaw[];
  navGroups: any[];
  routeNames: Record<string, string>;
  defaultRoute: string;
}

function searchApp(): ResolvedApp {
  return {
    routes: searchRoutes,
    navGroups: [searchNav.navGroup],
    routeNames: { ...searchNav.routeNames },
    defaultRoute: "/home"
  };
}

function mediaApp(): ResolvedApp {
  return {
    routes: mediaRoutes,
    // media 子包保留「基础配置 > 视频管理」层级外观，但只含媒体 4 项
    navGroups: [shellNav.baseConfigNavGroup([mediaNav.navGroup])],
    routeNames: { ...mediaNav.routeNames },
    defaultRoute: "/media"
  };
}

function controlApp(): ResolvedApp {
  return {
    routes: controlRoutes,
    navGroups: [controlNav.navGroup],
    routeNames: { ...controlNav.routeNames },
    defaultRoute: "/deployTasks"
  };
}

function reviewApp(): ResolvedApp {
  return {
    routes: reviewRoutes,
    navGroups: [reviewNav.navGroup],
    routeNames: { ...reviewNav.routeNames },
    defaultRoute: "/reviewTasks"
  };
}

// 全量应用装配。navGroups 顺序严格保持现状：总览、万物搜、万物核、算法布控、视觉事件、基础配置；
// 路由表顺序：overview → media → search → review → control → shell 其余（同改造前 router/index.ts）；
// routeNames 键序同理。
function fullApp(): ResolvedApp {
  return {
    routes: [
      overviewRoute,
      ...mediaRoutes,
      ...searchRoutes,
      ...reviewRoutes,
      ...controlRoutes,
      ...shellRoutes
    ],
    navGroups: [
      shellNav.overviewNavItem,
      searchNav.navGroup,
      reviewNav.navGroup,
      controlNav.navGroup,
      shellNav.eventsNavGroup,
      shellNav.baseConfigNavGroup([mediaNav.navGroup, ...shellNav.configNavItems])
    ],
    routeNames: {
      ...shellNav.overviewRouteNames,
      ...mediaNav.routeNames,
      ...searchNav.routeNames,
      ...reviewNav.routeNames,
      ...controlNav.routeNames,
      ...shellNav.routeNames
    },
    defaultRoute: "/home"
  };
}

export const MODULES: Record<string, ResolvedApp> = {
  search: searchApp(),
  media: mediaApp(),
  control: controlApp(),
  review: reviewApp()
};

export function resolveModules(env: { VITE_APP_MODULE?: string } = import.meta.env as { VITE_APP_MODULE?: string }): ResolvedApp {
  const key = (env && env.VITE_APP_MODULE) || "full";
  if (key === "full") return fullApp();
  return MODULES[key] || fullApp();
}

// 关键：MODE 在 vite build 时被静态替换为字面量（如 "media"），
// 下面三元表达式的死分支会被 Rollup 常量折叠 + tree-shake 整体移除，
// 使子包构建不含其它模块的路由、菜单文案与页面 chunk。
// 注意勿改成 import.meta.env?.VITE_APP_MODULE（可选链会破坏静态替换）。
const MODE: string = import.meta.env.VITE_APP_MODULE || "full";

// 本次构建的装配结果单例，store 与 router 共用
export const appModules: ResolvedApp =
  MODE === "search" ? searchApp() :
  MODE === "media" ? mediaApp() :
  MODE === "control" ? controlApp() :
  MODE === "review" ? reviewApp() :
  fullApp();
