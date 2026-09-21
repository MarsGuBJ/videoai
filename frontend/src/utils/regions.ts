// 设备管理共用工具：区域树（backend-media /api/regions）、密码强度、拉流地址拼装。

import { api } from "../api";
import type { RegionTreeNode } from "../api";

const STORAGE_KEY = "videoai.media.regions";

// 页面侧监控点树使用的扁平节点（由 flattenRegionTree 结果映射而来）
export type RegionNode = {
  name: string;
  fullPath: string;
  child: boolean;
  depth: number;
  count: number;
};

export type FlatRegionNode = {
  node: RegionTreeNode;
  name: string;
  fullPath: string;
  depth: number;
  count: number;
};

export function normalizePath(path: string): string {
  return String(path || "")
    .split("/")
    .map((segment) => segment.trim())
    .filter(Boolean)
    .join(" / ");
}

// 区域树深度优先展开：children 保持后端给定的 sortOrder 顺序；count = 该节点精确挂载的设备数
export function flattenRegionTree(tree: RegionTreeNode[]): FlatRegionNode[] {
  const out: FlatRegionNode[] = [];
  const walk = (nodes: RegionTreeNode[], prefix: string, depth: number) => {
    for (const node of nodes || []) {
      const fullPath = prefix ? `${prefix} / ${node.name}` : node.name;
      out.push({ node, name: node.name, fullPath, depth, count: node.deviceCount || 0 });
      walk(node.children || [], fullPath, depth + 1);
    }
  };
  walk(tree, "", 0);
  return out;
}

function readStoredRegionPaths(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const list = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(list)) return [];
    return list.filter((item) => typeof item === "string" && item.trim());
  } catch {
    return [];
  }
}

// 旧版 localStorage 自定义区域迁移到后端区域树：
// 每条路径逐段补齐缺失节点（已覆盖的路径跳过），全部完成后清除 localStorage
async function migrateStoredRegions(tree: RegionTreeNode[]): Promise<void> {
  const stored = readStoredRegionPaths();
  if (!stored.length) return;
  const idByPath = new Map<string, string>();
  flattenRegionTree(tree).forEach((item) => idByPath.set(item.fullPath, item.node.id));
  for (const raw of stored) {
    const path = normalizePath(raw);
    if (!path || idByPath.has(path)) continue;
    let prefix = "";
    let parentId: string | null = null;
    for (const segment of path.split(" / ")) {
      prefix = prefix ? `${prefix} / ${segment}` : segment;
      const existing = idByPath.get(prefix);
      if (existing) {
        parentId = existing;
        continue;
      }
      const created = await api.createRegion({ name: segment, parentId });
      idByPath.set(prefix, created.id);
      parentId = created.id;
    }
  }
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // localStorage 不可用时静默失败，下次加载会重试迁移（已存在的节点会被跳过）
  }
}

// 迁移只执行一次的并发保护：多个页面同时挂载时共享同一个迁移 Promise
let migrationPromise: Promise<void> | null = null;

// 加载区域树：首次调用时若存在旧版 localStorage 自定义区域，先迁移到后端再重新拉取
export async function loadRegionTree(): Promise<RegionTreeNode[]> {
  let tree = await api.regionTree();
  if (readStoredRegionPaths().length) {
    if (!migrationPromise) {
      migrationPromise = migrateStoredRegions(tree).finally(() => {
        migrationPromise = null;
      });
    }
    await migrationPromise;
    tree = await api.regionTree();
  }
  return tree;
}

export function passwordStrength(pwd?: string | null): { label: string; cls: string } {
  if (!pwd) return { label: "-", cls: "" };
  if (pwd.length < 8 || /^\d+$/.test(pwd)) return { label: "弱", cls: "weak" };
  const classes = [/[a-z]/, /[A-Z]/, /\d/, /[^a-zA-Z0-9]/].filter((rule) => rule.test(pwd)).length;
  if (pwd.length >= 10 && classes >= 3) return { label: "强", cls: "strong" };
  return { label: "中", cls: "medium" };
}

// 按协议拼装拉流地址；无法拼装的协议返回 null（需手动填写）。
export function computeSourceUrl(
  protocol?: string | null,
  ip?: string | null,
  port?: string | null,
  username?: string | null,
  password?: string | null
): string | null {
  const host = (ip || "").trim();
  if (!host) return null;
  const target = port && String(port).trim() ? `${host}:${String(port).trim()}` : host;
  const user = (username || "").trim();
  const auth = user ? `${encodeURIComponent(user)}${password ? `:${encodeURIComponent(password)}` : ""}@` : "";
  if (protocol === "RTSP 拉流") return `rtsp://${auth}${target}/`;
  if (protocol === "RTMP 推流") return `rtmp://${target}/live/`;
  if (protocol === "HTTP 拉流") return `http://${target}/`;
  return null;
}

// 可通过 IP+端口自动拼装拉流地址的协议
export function canComputeSourceUrl(protocol?: string | null): boolean {
  return protocol === "RTSP 拉流" || protocol === "RTMP 推流" || protocol === "HTTP 拉流";
}

// 从拉流地址解析连接要素（新增/编辑页输入后自动回填 IP/端口/用户名/密码）。
// 端口缺省时按协议取默认：rtsp=554、rtmp=1935、http=80、https=443。
export function parseSourceUrlParts(sourceUrl?: string | null): { ip?: string; port?: string; username?: string; password?: string } {
  const value = (sourceUrl || "").trim();
  if (!value) return {};
  const match = value.match(/^([a-zA-Z][a-zA-Z0-9+.-]*):\/\/(?:([^:@/]+)(?::([^@/]*))?@)?([^:/@\s]+)(?::(\d+))?/);
  if (!match) return {};
  const scheme = match[1].toLowerCase();
  const defaultPort = scheme === "rtsp" ? "554" : scheme === "rtmp" ? "1935" : scheme === "http" ? "80" : scheme === "https" ? "443" : undefined;
  const parts: { ip?: string; port?: string; username?: string; password?: string } = {};
  if (match[4]) parts.ip = decodeURIComponent(match[4]);
  const port = match[5] || defaultPort;
  if (port) parts.port = port;
  if (match[2]) parts.username = decodeURIComponent(match[2]);
  if (match[3]) parts.password = decodeURIComponent(match[3]);
  return parts;
}

// 拉流地址内嵌了用户名密码（值得调后端探测设备序列号/云台能力）
export function hasSourceUrlCredentials(sourceUrl?: string | null): boolean {
  return /^[a-zA-Z][a-zA-Z0-9+.-]*:\/\/[^:@/]+:[^@/]+@/.test((sourceUrl || "").trim());
}

// 设备通道号上限（常见 NVR/DVR 通道上限）
export const MAX_CHANNEL_NO = 256;

// IPv4 格式校验：四段数字，每段 0-255
export function isValidIPv4(value?: string | null): boolean {
  const v = (value || "").trim();
  if (!v) return false;
  const parts = v.split(".");
  if (parts.length !== 4) return false;
  return parts.every((part) => /^\d{1,3}$/.test(part) && Number(part) <= 255 && String(Number(part)) === part.replace(/^0+(?=\d)/, ""));
}

// 端口校验：纯数字，1-65535
export function isValidPort(value?: string | null): boolean {
  const v = (value || "").trim();
  if (!/^\d+$/.test(v)) return false;
  const n = Number(v);
  return n >= 1 && n <= 65535;
}

// 通道号校验：纯数字，1-MAX_CHANNEL_NO
export function isValidChannelNo(value?: string | null): boolean {
  const v = (value || "").trim();
  if (!/^\d+$/.test(v)) return false;
  const n = Number(v);
  return n >= 1 && n <= MAX_CHANNEL_NO;
}

// 国标域编码校验：20 位数字（GB/T 28181 编码）
export function isValidGbCode(value?: string | null): boolean {
  const v = (value || "").trim();
  return /^\d{20}$/.test(v);
}
