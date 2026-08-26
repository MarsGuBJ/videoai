// 算法布控模块菜单与路由名片段（从 store/index.ts 原样切出，文案一字不改）
export const navGroup = {
  title: "算法布控", icon: "\uf05b", items: [
    { key: "algorithms", label: "算法管理", icon: "\uf1b3" },
    { key: "deployTasks", label: "布控任务", icon: "\uf05b" }
  ]
};

export const routeNames = {
  algorithms: "算法管理",
  versionManager: "版本号管理",
  versionDetail: "版本号详情",
  previewFile: "预览文件",
  deployTasks: "布控任务",
  deployTaskDetail: "布控任务详情"
};
