import type { RouteRecordRaw } from "vue-router";

// 视频管理模块路由。页面文件保持在 ../../pages 原位，仅做逻辑分组；
// 保持现有懒加载风格，路由 name/path 与全量应用逐条一致。
export const routes: RouteRecordRaw[] = [
  { path: "/cameraList", name: "cameraList", component: () => import("../../pages/CameraListPage.vue") },
  { path: "/media", name: "media", component: () => import("../../pages/CameraListPage.vue") },
  { path: "/mediaDeviceWizard", name: "mediaDeviceWizard", component: () => import("../../pages/MediaDeviceWizardPage.vue") },
  { path: "/mediaDeviceDetail", name: "mediaDeviceDetail", component: () => import("../../pages/MediaDeviceDetailPage.vue") },
  { path: "/mediaDeviceEdit", name: "mediaDeviceEdit", component: () => import("../../pages/MediaDeviceEditPage.vue") },
  { path: "/mediaAccessConfig", name: "mediaAccessConfig", component: () => import("../../pages/MediaAccessConfigPage.vue") },
  { path: "/mediaCloudConfig", name: "mediaCloudConfig", component: () => import("../../pages/MediaCloudConfigPage.vue") },
  { path: "/mediaPreview", name: "mediaPreview", component: () => import("../../pages/MediaPreviewPage.vue") },
  { path: "/mediaPlayback", name: "mediaPlayback", component: () => import("../../pages/MediaPlaybackPage.vue") },
  { path: "/mediaWall", name: "mediaWall", component: () => import("../../pages/MediaWallPage.vue") },
  { path: "/mediaAlarm", name: "mediaAlarm", component: () => import("../../pages/MediaAlarmPage.vue") }
];
