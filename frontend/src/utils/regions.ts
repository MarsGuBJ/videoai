// 设备管理共用工具：自定义区域（localStorage）、区域树聚合、密码强度、拉流地址拼装。

const STORAGE_KEY = "videoai.media.regions";

export type RegionNode = {
  name: string;
  fullPath: string;
  child: boolean;
  count: number;
};

function normalizePath(path: string): string {
  return String(path || "")
    .split("/")
    .map((segment) => segment.trim())
    .filter(Boolean)
    .join(" / ");
}

export function loadCustomRegions(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const list = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(list)) return [];
    return list.filter((item) => typeof item === "string" && item.trim());
  } catch {
    return [];
  }
}

export function addCustomRegion(path: string): string[] {
  const value = normalizePath(path);
  const list = loadCustomRegions();
  if (value && !list.includes(value)) {
    list.push(value);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
  }
  return list;
}

// 由设备 area 列表 + 自定义区域聚合成扁平节点数组：
// 每条路径的每一级前缀都成为一个节点；child 表示非顶层节点；
// 顶层节点 count 含子孙，子节点 count 仅统计精确 area 匹配的设备数。
export function buildRegionTree(areas: string[], custom: string[]): RegionNode[] {
  const exactCounts = new Map<string, number>();
  const ordered: string[] = [];
  const seen = new Set<string>();
  const addPath = (raw: string, count: boolean) => {
    const path = normalizePath(raw);
    if (!path) return;
    if (count) exactCounts.set(path, (exactCounts.get(path) || 0) + 1);
    const segments = path.split(" / ");
    let prefix = "";
    for (const segment of segments) {
      prefix = prefix ? `${prefix} / ${segment}` : segment;
      if (!seen.has(prefix)) {
        seen.add(prefix);
        ordered.push(prefix);
      }
    }
  };
  areas.forEach((area) => addPath(area, true));
  custom.forEach((path) => addPath(path, false));
  return ordered.map((fullPath) => {
    const segments = fullPath.split(" / ");
    const child = segments.length > 1;
    let count = exactCounts.get(fullPath) || 0;
    if (!child) {
      // 顶层节点累加所有子孙的精确计数
      exactCounts.forEach((value, path) => {
        if (path !== fullPath && path.startsWith(fullPath + " / ")) count += value;
      });
    }
    return { name: segments[segments.length - 1], fullPath, child, count };
  });
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
