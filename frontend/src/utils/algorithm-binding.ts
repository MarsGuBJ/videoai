import type { Algorithm, DeploymentTask, EventInfo } from "../types";

/**
 * 布控算法解析：统一「事件编码 → 事件信息配置的算法编码 → 算法」这条链路，
 * 供新建/编辑布控任务弹窗、快速布防页、文搜视频快速布防 tab 与布控任务列表/
 * 详情页共用，避免各处口径不一致导致算法绑不上、列表里算法名称为空。
 */
export type AlgorithmResolution = {
  /** 事件信息配置里为该事件绑定的算法编码（未配置时为空串） */
  boundCode: string;
  /** 解析出的可布控算法；未匹配到时为 undefined */
  algorithm?: Algorithm;
  /** event=命中事件绑定的算法；code=算法编号本身即算法编码；none=未匹配 */
  source: "event" | "code" | "none";
};

const normalize = (value: unknown): string => String(value == null ? "" : value).trim();

/**
 * 解析某个算法编号（事件编码）对应的布控算法。
 *
 * 优先用事件信息配置里绑定的算法编码；事件没有绑定算法编码时，回落到
 * 「算法编号本身就是算法编码」的算法——否则用户在新建布控任务里明明选了
 * 算法编号，保存后列表里的算法名称却是空的。
 *
 * @param algorithms 算法清单（GET /api/algorithms）。
 * @param eventInfos 事件信息清单（GET /api/event-infos）。
 * @param eventCode  下拉框选中的算法编号（即事件编码）。
 * @returns 解析结果，含命中的算法与命中来源。
 */
export function resolveEventAlgorithm(
  algorithms: Algorithm[] | undefined,
  eventInfos: EventInfo[] | undefined,
  eventCode: unknown
): AlgorithmResolution {
  const list = algorithms || [];
  const code = normalize(eventCode);
  if (!code) return { boundCode: "", source: "none" };
  const eventInfo = (eventInfos || []).find(item => normalize(item.code) === code);
  const boundCode = normalize(eventInfo && eventInfo.algorithmCode);
  // 1) 事件信息配置里绑定的算法编码
  const byBinding = boundCode ? list.find(item => normalize(item.code) === boundCode) : undefined;
  if (byBinding) return { boundCode, algorithm: byBinding, source: "event" };
  // 2) 算法编号本身即算法编码
  const byCode = list.find(item => normalize(item.code) === code);
  if (byCode) return { boundCode, algorithm: byCode, source: "code" };
  return { boundCode, source: "none" };
}

/**
 * 取布控任务对应的算法：优先任务落库的 algorithmId，其次按 algorithmCode 在
 * 算法清单里匹配（兼容历史数据里 algorithmId/algorithmName 为空的任务）。
 *
 * @param task 布控任务（可为空）。
 * @param algorithms 算法清单。
 * @returns 命中的算法，未匹配到时为 undefined。
 */
export function algorithmOfTask(
  task: DeploymentTask | null | undefined,
  algorithms: Algorithm[] | undefined
): Algorithm | undefined {
  if (!task) return undefined;
  const list = algorithms || [];
  const byId = task.algorithmId ? list.find(item => item.id === task.algorithmId) : undefined;
  if (byId) return byId;
  const code = normalize(task.algorithmCode);
  return code ? list.find(item => normalize(item.code) === code) : undefined;
}

/**
 * 布控任务展示用的算法名称：算法清单名称 → 任务落库的 algorithmName →
 * pipeline → 「未绑定算法」。
 *
 * @param task 布控任务（可为空）。
 * @param algorithms 算法清单。
 * @returns 用于列表/详情展示的算法名称。
 */
export function algorithmNameOfTask(
  task: DeploymentTask | null | undefined,
  algorithms: Algorithm[] | undefined
): string {
  const algorithm = algorithmOfTask(task, algorithms);
  return (
    (algorithm && algorithm.name) ||
    normalize(task && task.algorithmName) ||
    normalize(task && task.pipeline) ||
    "未绑定算法"
  );
}
