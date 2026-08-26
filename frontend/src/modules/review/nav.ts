// 万物核模块菜单与路由名片段（从 store/index.ts 原样切出，文案一字不改）
export const navGroup = {
  title: "万物核", icon: "\uf046", items: [
    { key: "reviewTasks", label: "任务管理", icon: "\uf0ae" },
    { key: "reviewTypes", label: "复核类型管理", icon: "\uf0ca" }
  ]
};

export const routeNames = {
  reviewTasks: "任务管理",
  reviewTypes: "复核类型管理"
};
