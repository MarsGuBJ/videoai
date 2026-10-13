// 部署基路径运行时解析：构建统一使用相对 base（vite base: './'），同一套产物
// 既可直接以根路径部署在任意 IP/域名下（如 http://192.168.11.194:5173/），
// 也可经反代挂载在任意子路径下（如 https://域名/vision/），无需按部署点重新构建。
// 原理：所有构建产物（js/css chunk）都位于 <应用基路径>/assets/ 下，
// 由当前模块的真实加载地址反推基路径；仅显式配置了绝对 base 时才使用配置值。
export function resolveAppBase(): string {
  const configured = import.meta.env.BASE_URL;
  if (configured && configured !== "./" && configured !== "/") {
    return configured.endsWith("/") ? configured.slice(0, -1) : configured;
  }
  try {
    const url = new URL(import.meta.url);
    const m = url.pathname.match(/^(.*)\/assets\/[^/]+$/);
    if (m) return m[1] || "/";
  } catch {
    // 非浏览器环境等异常场景退回根路径
  }
  return "/";
}
