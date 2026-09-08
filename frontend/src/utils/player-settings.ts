// 播放器/视频参数设置：视频参数弹窗的持久化配置（localStorage）。
// 能立即生效的项：启动窗口（实时预览默认分屏）、抓图格式与命名（保存截图）、
// 即时回放时长（即时回放弹窗默认值）；其余项作为偏好持久化，待播放器支持后生效。

const SETTINGS_KEY = "videoai.media.playerSettings";

export type PlayerSettings = {
  savePath: string;
  startupLayout: number; // 启动窗口：1 | 4 | 9 | 16
  perfWarning: boolean; // 播放性能不足提示
  gpuDecode: boolean; // GPU 硬件解码
  recordWarning: boolean; // 录像预警提示
  multicast: boolean; // 是否组播
  reconnectCount: number; // 重连次数
  reconnectIntervalSec: number; // 重连间隔（秒）
  streamStrategy: string; // 码流策略：auto | main | sub
  perfThreshold: string; // 性能阈值
  instantReplaySec: number; // 即时回放时长（秒）：15 | 30 | 60
  recordFormat: string; // 录像格式：MP4 | FLV
  snapshotFormat: string; // 抓图格式：JPG | PNG
  namingRule: string; // 抓图命名规则（占位符：{设备名称} {时间}）
};

export const DEFAULT_PLAYER_SETTINGS: PlayerSettings = {
  savePath: "C:/Users/Public/AVPreview",
  // 启动窗口默认单画面（实时预览页默认 1 个屏幕）
  startupLayout: 1,
  perfWarning: true,
  gpuDecode: false,
  recordWarning: false,
  multicast: false,
  reconnectCount: 10,
  reconnectIntervalSec: 15,
  streamStrategy: "auto",
  perfThreshold: "cpu80",
  instantReplaySec: 15,
  recordFormat: "MP4",
  snapshotFormat: "JPG",
  namingRule: "{设备名称}_{时间}"
};

const STARTUP_LAYOUTS = [1, 4, 9, 16];
const REPLAY_SECONDS = [15, 30, 60];

function sanitize(raw: any): PlayerSettings {
  const base = { ...DEFAULT_PLAYER_SETTINGS, ...(raw || {}) };
  if (!STARTUP_LAYOUTS.includes(Number(base.startupLayout))) base.startupLayout = DEFAULT_PLAYER_SETTINGS.startupLayout;
  if (!REPLAY_SECONDS.includes(Number(base.instantReplaySec))) base.instantReplaySec = DEFAULT_PLAYER_SETTINGS.instantReplaySec;
  base.startupLayout = Number(base.startupLayout);
  base.instantReplaySec = Number(base.instantReplaySec);
  base.reconnectCount = Math.max(0, Number(base.reconnectCount) || 0);
  base.reconnectIntervalSec = Math.max(1, Number(base.reconnectIntervalSec) || DEFAULT_PLAYER_SETTINGS.reconnectIntervalSec);
  base.snapshotFormat = base.snapshotFormat === "PNG" ? "PNG" : "JPG";
  base.recordFormat = base.recordFormat === "FLV" ? "FLV" : "MP4";
  return base;
}

export function loadPlayerSettings(): PlayerSettings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    return sanitize(raw ? JSON.parse(raw) : null);
  } catch {
    return { ...DEFAULT_PLAYER_SETTINGS };
  }
}

export function savePlayerSettings(settings: PlayerSettings): void {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(sanitize(settings)));
  } catch {
    // localStorage 不可用时忽略
  }
}

export function resetPlayerSettings(): PlayerSettings {
  const defaults = { ...DEFAULT_PLAYER_SETTINGS };
  savePlayerSettings(defaults);
  return defaults;
}

// 按命名规则生成抓图文件名（不含扩展名）。
// 支持占位符 {设备名称} {通道} {时间}；时间格式 yyyyMMdd_HHmmss。
export function snapshotFileName(rule: string, deviceName: string, channel?: string): string {
  const now = new Date();
  const pad = (n: number) => n.toString().padStart(2, "0");
  const timeText = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
  const template = (rule || DEFAULT_PLAYER_SETTINGS.namingRule).trim() || DEFAULT_PLAYER_SETTINGS.namingRule;
  const name = template
    .replace(/\{设备名称\}|设备名称/g, deviceName || "画面")
    .replace(/\{通道\}|通道/g, channel || "通道_1")
    .replace(/\{时间\}|时间/g, timeText);
  // 去掉文件名非法字符
  return name.replace(/[\\/:*?"<>|]/g, "_");
}
