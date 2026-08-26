// 视频管理模块菜单与路由名片段（从 store/index.ts 原样切出，文案一字不改）。
// 菜单挂在「基础配置 > 视频管理」子组下，层级外壳由装配工厂拼接。
export const navGroup = {
  title: "视频管理", icon: "\uf03d", items: [
    { key: "media", label: "设备管理", icon: "\uf1b2" },
    { key: "mediaAccessConfig", label: "接入配置", icon: "\uf1e6" },
    { key: "mediaCloudConfig", label: "云平台配置", icon: "\uf0c2" },
    { key: "mediaPreview", label: "实时预览", icon: "\uf03d" },
    { key: "mediaPlayback", label: "录像回放", icon: "\uf017" }
  ]
};

export const routeNames = {
  cameraList: "视频管理",
  media: "视频管理",
  mediaDeviceWizard: "新增设备",
  mediaDeviceDetail: "设备详情",
  mediaDeviceEdit: "编辑设备",
  mediaAccessConfig: "接入配置",
  mediaCloudConfig: "云平台配置",
  mediaPreview: "实时预览",
  mediaPlayback: "录像回放",
  mediaWall: "电视墙",
  mediaAlarm: "告警联动"
};
