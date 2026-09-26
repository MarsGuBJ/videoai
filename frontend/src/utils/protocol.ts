// 设备「接入协议」词汇表：筛选下拉、设备表单、表格展示、批量导入导出统一取这里，
// 避免出现「表格显示 RTSP、下拉框却只有 RTSP 拉流」这类两套词汇对不上的问题。
// 后端历史数据里存在 RTSP / GB28181 这类短码（早期批量导入写入），
// 展示、筛选、回填表单、导入落库前一律先用 normalizeProtocol 归一化。

/** 接入协议可选文案（与后端 NvrImportServiceImpl 写入的 PROTOCOL_RTSP 文案保持一致）。 */
export const PROTOCOL_OPTIONS = [
  "海康 SDK",
  "大华 SDK",
  "GB28181",
  "ONVIF",
  "Ehome / ISUP 5.0",
  "RTSP 拉流",
  "RTMP 推流",
  "HTTP 拉流",
  "GA/T 1400"
];

// 别名 -> 展示文案。键统一为「小写并去掉空格/_/-//」，
// 因此 RTSP、rtsp_pull、RTSP 拉流 会命中同一项。
const PROTOCOL_LABELS: Record<string, string> = {};

function aliasKey(value: string): string {
  return value.toLowerCase().replace(/[\s_/-]/g, "");
}

function registerProtocol(label: string, aliases: string[]): void {
  [label, ...aliases].forEach((alias) => {
    PROTOCOL_LABELS[aliasKey(alias)] = label;
  });
}

registerProtocol("海康 SDK", ["HIKVISION", "HIK", "海康", "海康sdk"]);
registerProtocol("大华 SDK", ["DAHUA", "大华", "大华sdk"]);
registerProtocol("GB28181", ["GB/T 28181", "GB/T 28181-2022", "GB28181-2016", "国标GB28181"]);
registerProtocol("ONVIF", ["ONVIF Profile S"]);
registerProtocol("Ehome / ISUP 5.0", ["EHOME", "ISUP", "ISUP 5.0", "Ehome"]);
registerProtocol("RTSP 拉流", ["RTSP", "RTSP_PULL"]);
registerProtocol("RTMP 推流", ["RTMP"]);
registerProtocol("HTTP 拉流", ["HTTP", "HTTPS"]);
registerProtocol("GA/T 1400", ["GA1400", "GA/T1400"]);

/**
 * 归一化接入协议：短码/别名映射为下拉框文案。
 *
 * @param value 原始协议值（后端字段或导入表格单元格）。
 * @returns 归一化后的文案；未识别的自定义值原样返回（不丢数据），空值返回空串。
 */
export function normalizeProtocol(value?: string | null): string {
  const text = String(value ?? "").trim();
  if (!text) return "";
  return PROTOCOL_LABELS[aliasKey(text)] || text;
}
