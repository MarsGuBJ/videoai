// 设备状态展示口径（后端 V16 起把两个维度拆开）：
//   onlineStatus —— 设备可达性：ONLINE 在线 / OFFLINE 离线 / UNKNOWN 未探测（扫描无法判定）
//   status       —— 拉流状态：RUNNING 拉流中 / STOPPED 已停止 / DISABLED 停用
// 页面上的「在线 / 离线」一律指设备可达性（onlineStatus），拉流状态单独用 streamStatusLabel 展示，
// 避免把"设备在线但没在拉流"误显示成"离线"。

export type DeviceOnlineStatus = "ONLINE" | "OFFLINE" | "UNKNOWN";

type CameraLike = { onlineStatus?: string | null; status?: string | null } | null | undefined;

export function onlineStatusOf(camera: CameraLike): DeviceOnlineStatus {
  const value = String((camera && camera.onlineStatus) || "").toUpperCase();
  if (value === "ONLINE" || value === "OFFLINE") return value;
  return "UNKNOWN";
}

/** 设备可达性中文标签：在线 / 离线 / 未探测。 */
export function deviceStatusLabel(camera: CameraLike): string {
  const value = onlineStatusOf(camera);
  if (value === "ONLINE") return "在线";
  if (value === "OFFLINE") return "离线";
  return "未探测";
}

/** 设备可达性对应的样式类（媒体树 / 状态点共用）。 */
export function deviceStatusClass(camera: CameraLike): string {
  return onlineStatusOf(camera) === "ONLINE" ? "online" : "offline";
}

/** 排序权重：在线在前，未探测居中，离线在后。 */
export function deviceStatusRank(camera: CameraLike): number {
  const value = onlineStatusOf(camera);
  if (value === "ONLINE") return 0;
  if (value === "UNKNOWN") return 1;
  return 2;
}

/** 拉流状态中文标签：拉流中 / 拉流中断 / 已停止 / 停用 / 未启动。 */
export function streamStatusLabel(camera: CameraLike): string {
  const status = String((camera && camera.status) || "").toUpperCase();
  if (status === "DISABLED") return "停用";
  if (status === "RUNNING") {
    return onlineStatusOf(camera) === "OFFLINE" ? "拉流中断" : "拉流中";
  }
  if (status === "STOPPED") return "已停止";
  if (status === "OFFLINE") return "拉流中断";
  return "未启动";
}

/** 是否正在拉流（RUNNING）；设备离线时流必然中断。 */
export function isStreaming(camera: CameraLike): boolean {
  return String((camera && camera.status) || "").toUpperCase() === "RUNNING";
}
