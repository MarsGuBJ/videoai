import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

// Route table derived from the prototype App's currentComponent map
// (offline-package/index.html lines ~15248-15290) and store.routeNames.
// One route per page: path "/<routeName>", name = routeName.
// Page components are converted from the prototype components by name.
const routes: RouteRecordRaw[] = [
  { path: "/", redirect: "/home" },
  { path: "/overview", name: "overview", component: () => import("../pages/OverviewPage.vue") },
  { path: "/cameraList", name: "cameraList", component: () => import("../pages/CameraListPage.vue") },
  { path: "/media", name: "media", component: () => import("../pages/CameraListPage.vue") },
  { path: "/mediaDeviceWizard", name: "mediaDeviceWizard", component: () => import("../pages/MediaDeviceWizardPage.vue") },
  { path: "/mediaDeviceDetail", name: "mediaDeviceDetail", component: () => import("../pages/MediaDeviceDetailPage.vue") },
  { path: "/mediaDeviceEdit", name: "mediaDeviceEdit", component: () => import("../pages/MediaDeviceEditPage.vue") },
  { path: "/mediaAccessConfig", name: "mediaAccessConfig", component: () => import("../pages/MediaAccessConfigPage.vue") },
  { path: "/mediaPreview", name: "mediaPreview", component: () => import("../pages/MediaPreviewPage.vue") },
  { path: "/mediaPlayback", name: "mediaPlayback", component: () => import("../pages/MediaPlaybackPage.vue") },
  { path: "/mediaWall", name: "mediaWall", component: () => import("../pages/MediaWallPage.vue") },
  { path: "/mediaAlarm", name: "mediaAlarm", component: () => import("../pages/MediaAlarmPage.vue") },
  { path: "/home", name: "home", component: () => import("../pages/HomePage.vue") },
  { path: "/exact", name: "exact", component: () => import("../pages/ExactSearchPage.vue") },
  { path: "/localVideo", name: "localVideo", component: () => import("../pages/LocalVideoPage.vue") },
  { path: "/textImage", name: "textImage", component: () => import("../pages/TextImagePage.vue") },
  { path: "/imageSearch", name: "imageSearch", component: () => import("../pages/ImageSearchPage.vue") },
  { path: "/quickDeploy", name: "quickDeploy", component: () => import("../pages/QuickDeployPage.vue") },
  { path: "/track", name: "track", component: () => import("../pages/TrackPage.vue") },
  { path: "/monitorSearch", name: "monitorSearch", component: () => import("../pages/MonitorSearchPage.vue") },
  { path: "/reviewTasks", name: "reviewTasks", component: () => import("../pages/ReviewTasksPage.vue") },
  { path: "/reviewTypes", name: "reviewTypes", component: () => import("../pages/ReviewTypesPage.vue") },
  { path: "/algorithms", name: "algorithms", component: () => import("../pages/AlgorithmsPage.vue") },
  { path: "/versionManager", name: "versionManager", component: () => import("../pages/VersionManagerPage.vue") },
  { path: "/versionDetail", name: "versionDetail", component: () => import("../pages/VersionDetailPage.vue") },
  { path: "/previewFile", name: "previewFile", component: () => import("../pages/PreviewFilePage.vue") },
  { path: "/deployTasks", name: "deployTasks", component: () => import("../pages/DeployTasksPage.vue") },
  { path: "/deployTaskDetail", name: "deployTaskDetail", component: () => import("../pages/DeployTaskDetailPage.vue") },
  { path: "/events", name: "events", component: () => import("../pages/EventsPage.vue") },
  { path: "/eventDetail", name: "eventDetail", component: () => import("../pages/EventDetailPage.vue") },
  { path: "/stats", name: "stats", component: () => import("../pages/StatsPage.vue") },
  { path: "/eventConfig", name: "eventConfig", component: () => import("../pages/EventConfigPage.vue") },
  { path: "/eventConfigInfo", name: "eventConfigInfo", component: () => import("../pages/EventConfigInfoPage.vue") },
  { path: "/eventConfigIngestion", name: "eventConfigIngestion", component: () => import("../pages/EventConfigIngestionPage.vue") },
  { path: "/eventConfigDedup", name: "eventConfigDedup", component: () => import("../pages/EventConfigDedupPage.vue") },
  { path: "/eventConfigSubscriptions", name: "eventConfigSubscriptions", component: () => import("../pages/EventConfigSubscriptionsPage.vue") },
  { path: "/modelConfig", name: "modelConfig", component: () => import("../pages/ModelConfigPage.vue") },
  { path: "/resource", name: "resource", component: () => import("../pages/ResourcePage.vue") },
  { path: "/logs", name: "logs", component: () => import("../pages/LogsPage.vue") },
  { path: "/permissions", name: "permissions", component: () => import("../pages/PermissionsPage.vue") },
  { path: "/:pathMatch(.*)*", redirect: "/" }
];

export const router = createRouter({
  history: createWebHistory(),
  routes
});

export default router;
