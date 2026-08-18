// Helpers ported verbatim from the prototype (index.html lines 10187-10212).
// In the prototype these were global functions / app.config.globalProperties;
// SFCs import them from here instead.

export function statusClass(status: string): string {
  if (status === "待复核" || status === "待处理" || status === "待发布" || status === "暂停") return "waiting";
  if (status === "复核中" || status === "进行中" || status === "运行中" || status === "测试中" || status === "处理中" || status === "繁忙" || status === "同步中") return "processing";
  if (status === "有效" || status === "已通过" || status === "启用" || status === "已完成" || status === "已发布" || status === "已处理" || status === "运行良好" || status === "在线" || status === "空闲" || status === "成功" || status === "执行成功") return "pass";
  if (status === "无效" || status === "未成功连接" || status === "已驳回" || status === "停用" || status === "已停用" || status === "已停止" || status === "已暂停" || status === "已结束" || status === "已关闭" || status === "连接异常" || status === "连接失败" || status === "离线" || status === "失败" || status === "执行失败") return "reject";
  return "";
}

export function similarityColor(score: number): string {
  const value = Math.min(100, Math.max(0, Number(score) || 0));
  return `hsl(${value * 1.2} 72% 38%)`;
}
