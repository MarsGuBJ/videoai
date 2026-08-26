// 万物搜模块菜单与路由名片段（从 store/index.ts 原样切出，文案一字不改）
export const navGroup = {
  title: "万物搜", icon: "\uf002", items: [
    { key: "exact", label: "文搜视频", icon: "\uf03d" },
    { key: "textImage", label: "文搜图", icon: "\uf1c5" },
    { key: "imageSearch", label: "图搜图", icon: "\uf1e5" },
    { key: "track", label: "轨迹还原", icon: "\uf279" }
  ]
};

export const routeNames = {
  home: "万物搜主页",
  exact: "文搜视频",
  localVideo: "视频分析",
  textImage: "文搜图",
  imageSearch: "图搜图",
  quickDeploy: "快速布防",
  track: "轨迹还原",
  monitorSearch: "监控搜索"
};
