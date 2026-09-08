import type { AccessCertificate, AccessConfig, AccessGa1400Entry, AccessGb28181Config, AccessGb28181Entry, Algorithm, AlgorithmEngine, AlgorithmVersion, Camera, CloudDeviceItem, CloudPlatform, CloudSyncPrecheck, CloudSyncResult, DedupRule, DedupRulePayload, DeploymentEventPage, DeploymentEventQuery, DeploymentEventStats, DeploymentEventStatsQuery, DeploymentEventSummary, DeploymentTask, DeploymentTaskCreate, EventInfo, EventInfoPayload, FaceEvent, FaceProfile, LlmConfig, LlmConfigPayload, LlmTestResult, ModelGpuConfig, ModelInfo, PtzCommandRequest, PtzCommandResponse, PushTask, PushTaskPayload, ReviewSchedule, ReviewTask, ReviewType, SearchKeywordStatItem, WindowsCameraStatus, WorkerNode } from '../types';

export type {
  AccessCertificate,
  AccessConfig,
  AccessGa1400Config,
  AccessGa1400Entry,
  AccessGb28181Config,
  AccessGb28181Entry,
  Algorithm,
  AlgorithmEngine,
  AlgorithmVersion,
  Camera,
  DeploymentEvent,
  DeploymentEventPage,
  DeploymentEventStats,
  DeploymentEventSummary,
  DeploymentTask,
  DeploymentTaskCreate,
  FaceEvent,
  FaceProfile,
  ModelGpuConfig,
  ModelInfo,
  PtzCommand,
  PtzCommandRequest,
  PtzCommandResponse,
  WindowsCameraStatus,
} from '../types';

export const API_BASE_URL = resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL);
export const MEDIA_API_BASE_URL = resolveApiBaseUrl(import.meta.env.VITE_MEDIA_API_BASE_URL);

const MEDIA_API_PATH_PREFIXES = ['/api/cameras', '/api/live', '/api/streams', '/api/access-config', '/api/cloud-platforms'];

function isMediaApiPath(path: string): boolean {
  return MEDIA_API_PATH_PREFIXES.some((prefix) => path.startsWith(prefix));
}

function baseUrlForPath(path: string): string {
  return isMediaApiPath(path) ? MEDIA_API_BASE_URL : API_BASE_URL;
}

type CameraPayload = {
  name?: string;
  sourceUrl?: string;
  description?: string;
  area?: string;
  nvrId?: string;
  nvrChannel?: string;
  nvrTrackId?: string;
  nvrStreamType?: string;
  protocol?: string;
  vendor?: string;
  ip?: string;
  port?: string;
  username?: string;
  password?: string;
  deviceCode?: string;
  serialNumber?: string;
  videoPreviewEnabled?: boolean;
  audioEnabled?: boolean;
  talkbackEnabled?: boolean;
  ptzEnabled?: boolean;
  smartAnalysisEnabled?: boolean;
  alarmIoEnabled?: boolean;
};

type CloudPlatformPayload = {
  name?: string;
  type?: string;
  key?: string;
  secret?: string;
  ip?: string;
  port?: string;
};

type ReviewTypePayload = {
  name?: string;
  code?: string;
  prompt?: string;
  injectEvent?: string;
  remark?: string;
  llmConfigId?: string | null;
};

type ReviewSchedulePayload = {
  name?: string;
  reviewTypeId?: string;
  cron?: string;
  enabled?: boolean;
  batchSize?: number;
};

export type PersonSearchBboxPoint = {
  x: number;
  y: number;
};

export type DetectedPerson = {
  person_id?: string;
  bbox: PersonSearchBboxPoint[];
  confidence?: number;
  class_id?: number;
};

export type PersonDetectResponse = {
  code?: number;
  message?: string;
  data?: {
    status?: string;
    message?: string;
    detected_persons?: DetectedPerson[];
    image_shape?: number[];
  };
};

export type PersonSearchSubmitResponse = {
  code?: number;
  message?: string;
  data?: {
    status?: string;
    message?: string;
    task_id?: string;
    data?: {
      task_id?: string;
    };
  };
};

export type SimilarPersonResult = {
  es_doc_id?: string;
  similarity_score?: number;
  create_time?: number | string;
  camera_id?: string;
  camera_locate?: string;
  image_url?: string;
};

export type PersonSearchResultResponse = {
  code?: number;
  message?: string;
  data?: {
    status?: string;
    message?: string;
    data?: {
      status?: string;
      message?: string;
      processed_bboxes?: PersonSearchBboxPoint[][];
      search_method?: string;
      similar_persons?: SimilarPersonResult[];
      result?: {
        status?: string;
        message?: string;
        processed_bboxes?: PersonSearchBboxPoint[][];
        search_method?: string;
        similar_persons?: SimilarPersonResult[];
      };
    } | null;
  };
};

export type TextSearchItemPayload = {
  image_url?: string;
  camera_locate?: string;
  camera_id?: string;
  create_time?: number | string;
  top_color?: string[];
  bottom_color?: string[];
  top_type?: string;
  bottom_type?: string;
  sex?: string;
  [key: string]: unknown;
};

export type TextSearchItem = {
  document_id?: string;
  esid?: string;
  index?: string;
  source?: string;
  score?: number | null;
  payload?: TextSearchItemPayload;
};

export type TextSearchQueryResponse = {
  code?: number;
  message?: string;
  data?: {
    session_id?: string;
    trace_id?: string | null;
    index?: string | null;
    total?: number;
    items?: TextSearchItem[];
  };
};

// MinIO 视频智能分析响应格式未在接口文档中给出，按宽容结构解析。
export type VideoAnalysisResponse = {
  code?: number;
  message?: string;
  data?: unknown;
  result?: unknown;
  text?: unknown;
  analysis?: unknown;
  [key: string]: unknown;
};

// NVR 录像导出为 MP4 文件后的响应（backend-lite 透传 MCP export_recording 的 data）。
export type RecordingFileResponse = {
  videoUrl: string;
  durationSeconds?: number;
  trackId?: string;
  startTime?: string;
  endTime?: string;
};

// NVR 录像回放接口（backend-lite /api/recordings/*）：时间段均为北京时间 ISO 字符串。
export type RecordingSegment = {
  recordingId?: string;
  cameraId: string;
  cameraName?: string;
  trackId?: string;
  startTime: string;
  endTime: string;
  url?: string;
  format?: string;
};

export type RecordingSearchResponse = {
  data: RecordingSegment[];
};

export type RecordingStreamResult = {
  url: string;
  format: string;
  expiresAt?: string;
};

export type RecordingDownloadResult = {
  url: string;
  format: string;
};

export type RecordingTimeRangePayload = {
  cameraId: string;
  startTime: string;
  endTime: string;
  /** 回放倍速（仅 stream 接口使用），现场海康 NVR 实测支持 0.25/0.5/1/2/4/8/16/32 */
  speed?: number;
};

function extractErrorMessage(text: string, response: Response): string {
  if (!text) return `${response.status} ${response.statusText}`;
  try {
    const body = JSON.parse(text);
    const detail = body && body.detail;
    if (typeof detail === 'string') return detail;
    if (detail && typeof detail.message === 'string') return detail.message;
    if (detail && detail.error && typeof detail.error.message === 'string') return detail.error.message;
    if (body && typeof body.message === 'string') return body.message;
  } catch {
    // 非 JSON 错误体，原样返回
  }
  return text;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${baseUrlForPath(path)}${path}`, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...options.headers,
    },
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(extractErrorMessage(text, response));
  }
  if (response.status === 204) {
    return undefined as T;
  }
  const text = await response.text();
  return text ? (JSON.parse(text) as T) : (undefined as T);
}

// 摄像头列表 30 秒短缓存：各页面区域/监控点树共用，避免每次挂载重复拉取全量列表；
// 增删改/启停摄像头后立即失效，失败响应不留缓存
const CAMERAS_CACHE_TTL_MS = 30_000;
let camerasCache: { at: number; promise: Promise<Camera[]> } | null = null;

function invalidateCamerasCache() {
  camerasCache = null;
}

function fetchCamerasCached(): Promise<Camera[]> {
  const now = Date.now();
  if (camerasCache && now - camerasCache.at < CAMERAS_CACHE_TTL_MS) return camerasCache.promise;
  const promise = request<Camera[]>('/api/cameras').catch((error) => {
    if (camerasCache?.promise === promise) camerasCache = null;
    throw error;
  });
  camerasCache = { at: now, promise };
  return promise;
}

export const api = {
  cameras: () => fetchCamerasCached(),
  camera: (id: string) => request<Camera>(`/api/cameras/${id}`),
  createCamera: (payload: CameraPayload) =>
    request<Camera>('/api/cameras', { method: 'POST', body: JSON.stringify(payload) }).then((cam) => {
      invalidateCamerasCache();
      return cam;
    }),
  updateCamera: (id: string, payload: CameraPayload) =>
    request<Camera>(`/api/cameras/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }).then((cam) => {
      invalidateCamerasCache();
      return cam;
    }),
  deleteCamera: (id: string) =>
    request<void>(`/api/cameras/${id}`, { method: 'DELETE' }).then((result) => {
      invalidateCamerasCache();
      return result;
    }),
  startCamera: (id: string) =>
    request<Camera>(`/api/cameras/${id}/start`, { method: 'POST' }).then((cam) => {
      invalidateCamerasCache();
      return cam;
    }),
  stopCamera: (id: string) =>
    request<Camera>(`/api/cameras/${id}/stop`, { method: 'POST' }).then((cam) => {
      invalidateCamerasCache();
      return cam;
    }),
  ptzControl: (id: string, payload: PtzCommandRequest) =>
    request<PtzCommandResponse>(`/api/cameras/${id}/ptz`, { method: 'POST', body: JSON.stringify(payload) }),

  faces: () => request<FaceProfile[]>('/api/faces'),
  createFace: (form: FormData) => request<FaceProfile>('/api/faces', { method: 'POST', body: form }),
  updateFace: (id: string, form: FormData) => request<FaceProfile>(`/api/faces/${id}`, { method: 'PATCH', body: form }),
  deleteFace: (id: string) => request<void>(`/api/faces/${id}`, { method: 'DELETE' }),

  events: () => request<FaceEvent[]>('/api/events?limit=100'),
  deploymentEvents: (params: DeploymentEventQuery = {}) => {
    const search = new URLSearchParams();
    search.set('page', String(params.page ?? 1));
    search.set('size', String(params.size ?? 20));
    if (params.taskId) search.set('taskId', params.taskId);
    if (params.cameraId) search.set('cameraId', params.cameraId);
    if (params.eventType) search.set('eventType', params.eventType);
    if (params.keyword) search.set('keyword', params.keyword);
    if (params.startTime) search.set('startTime', params.startTime);
    if (params.endTime) search.set('endTime', params.endTime);
    return request<DeploymentEventPage>(`/api/deployment-events?${search.toString()}`);
  },
  deploymentEventSummary: () => request<DeploymentEventSummary>('/api/deployment-events/summary'),
  deploymentEventStats: (params: DeploymentEventStatsQuery = {}) => {
    const search = new URLSearchParams();
    if (params.startTime) search.set('startTime', params.startTime);
    if (params.endTime) search.set('endTime', params.endTime);
    if (params.area) search.set('area', params.area);
    const query = search.toString();
    return request<DeploymentEventStats>(`/api/deployment-events/stats${query ? `?${query}` : ''}`);
  },

  searchKeywordStats: (limit = 10) =>
    request<SearchKeywordStatItem[]>(`/api/search-keywords/stats?limit=${limit}`),

  models: () => request<ModelInfo[]>('/api/models'),
  registerModel: (payload: { name: string; displayName: string; repositoryPath?: string; modelType: string; description?: string }) =>
    request<ModelInfo>('/api/models/register', { method: 'POST', body: JSON.stringify(payload) }),
  loadModel: (name: string) => request<ModelInfo>(`/api/models/${name}/load`, { method: 'POST' }),
  unloadModel: (name: string) => request<ModelInfo>(`/api/models/${name}/unload`, { method: 'POST' }),
  modelConfig: (name: string) => request<{ name: string; config: Record<string, unknown> }>(`/api/models/${name}/config`),
  modelGpu: (name: string) => request<ModelGpuConfig>(`/api/models/${name}/gpu`),
  updateModelGpu: (name: string, gpuIds: number[]) =>
    request<ModelGpuConfig>(`/api/models/${name}/gpu`, { method: 'PATCH', body: JSON.stringify({ gpuIds }) }),

  windowsCameraStatus: () => request<WindowsCameraStatus>('/api/windows-camera/status'),
  startWindowsCamera: (payload?: { deviceName?: string; streamName?: string }) =>
    request<WindowsCameraStatus>('/api/windows-camera/start', { method: 'POST', body: JSON.stringify(payload ?? {}) }),
  stopWindowsCamera: () => request<WindowsCameraStatus>('/api/windows-camera/stop', { method: 'POST' }),

  deploymentTasks: () => request<DeploymentTask[]>('/api/deployment-tasks'),
  createDeploymentTask: (payload: DeploymentTaskCreate) =>
    request<DeploymentTask>('/api/deployment-tasks', { method: 'POST', body: JSON.stringify(payload) }),
  updateDeploymentTask: (id: string, payload: Partial<DeploymentTaskCreate>) =>
    request<DeploymentTask>(`/api/deployment-tasks/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteDeploymentTask: (id: string) =>
    request<{ deleted: string }>(`/api/deployment-tasks/${id}`, { method: 'DELETE' }),

  algorithmEngines: () => request<AlgorithmEngine[]>('/api/algorithm-engines'),
  algorithms: () => request<Algorithm[]>('/api/algorithms'),
  createAlgorithm: (form: FormData) => request<Algorithm>('/api/algorithms', { method: 'POST', body: form }),
  updateAlgorithm: (id: string, payload: { name?: string; scene?: string; owner?: string; description?: string; status?: 'RUNNING' | 'DISABLED' }) =>
    request<Algorithm>(`/api/algorithms/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  algorithmVersions: (id: string) => request<AlgorithmVersion[]>(`/api/algorithms/${encodeURIComponent(id)}/versions`),
  createAlgorithmVersion: (id: string, form: FormData) =>
    request<AlgorithmVersion>(`/api/algorithms/${encodeURIComponent(id)}/versions`, { method: 'POST', body: form }),
  activateAlgorithmVersion: (id: string, versionId: string) =>
    request<AlgorithmVersion>(`/api/algorithms/${encodeURIComponent(id)}/versions/${encodeURIComponent(versionId)}/activate`, { method: 'POST' }),

  uploadPersonSearchImage: (image: File) => {
    const form = new FormData();
    form.append('image', image);
    return request<{ imageUrl: string; imagePath: string }>('/api/person-search/images', { method: 'POST', body: form });
  },
  detectPersons: (imageUrl: string) =>
    request<PersonDetectResponse>('/api/person-search/detect-persons', {
      method: 'POST',
      body: JSON.stringify({ imageUrl }),
    }),
  searchPersonByBbox: (payload: {
    imageUrl: string;
    bbox?: PersonSearchBboxPoint[];
    searchMethod: 'reid' | 'vlm';
    startTime?: string;
    endTime?: string;
    similarityThreshold: number;
    topK: number;
  }) =>
    request<PersonSearchSubmitResponse>('/api/person-search/search-by-bbox', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  personSearchResult: (taskId: string) =>
    request<PersonSearchResultResponse>(`/api/person-search/results/${encodeURIComponent(taskId)}`),

  textSearchQuery: (payload: {
    message: string;
    startTime?: string;
    endTime?: string;
    location?: string;
    page?: number;
    pageSize?: number;
  }) =>
    request<TextSearchQueryResponse>('/api/text-search/query', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  analyzeMinioVideo: (payload: {
    videoUrl: string;
    prompt: string;
    fps?: number;
    segmentSeconds?: number;
    maxSegments?: number;
    height?: number;
  }) =>
    request<VideoAnalysisResponse>('/api/video-analysis/analyze', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getRecordingFileUrl: (payload: { cameraId: string; startTime: string; endTime: string }) =>
    request<RecordingFileResponse>('/api/video-analysis/recording-file', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  searchRecordings: (payload: RecordingTimeRangePayload) =>
    request<RecordingSearchResponse>('/api/recordings/search', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  startRecordingStream: (payload: RecordingTimeRangePayload) =>
    request<RecordingStreamResult>('/api/recordings/stream', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  downloadRecording: (payload: RecordingTimeRangePayload) =>
    request<RecordingDownloadResult>('/api/recordings/download', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  uploadAnalysisVideo: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<{ videoUrl: string }>('/api/video-analysis/upload-video', { method: 'POST', body: form });
  },

  accessConfig: () => request<AccessConfig>('/api/access-config'),
  gb28181Entries: () => request<AccessGb28181Entry[]>('/api/access-config/gb28181/entries'),
  createGb28181Entry: (payload: { enabled: boolean; sipId: string; sipDomain: string; sipIp: string; sipPort: string; password: string; parentPort: string; receivePortStart: string; receivePortEnd: string }) =>
    request<AccessGb28181Entry>('/api/access-config/gb28181/entries', { method: 'POST', body: JSON.stringify(payload) }),
  updateGb28181Entry: (id: string, payload: { enabled: boolean; sipId: string; sipDomain: string; sipIp: string; sipPort: string; password: string; parentPort: string; receivePortStart: string; receivePortEnd: string }) =>
    request<AccessGb28181Entry>(`/api/access-config/gb28181/entries/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteGb28181Entry: (id: string) =>
    request<void>(`/api/access-config/gb28181/entries/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  ga1400Entries: () => request<AccessGa1400Entry[]>('/api/access-config/ga1400/entries'),
  createGa1400Entry: (payload: { enabled: boolean; platformId: string; platformIp: string; port: string; password: string; resourcePath: string; autoRegister: boolean }) =>
    request<AccessGa1400Entry>('/api/access-config/ga1400/entries', { method: 'POST', body: JSON.stringify(payload) }),
  updateGa1400Entry: (id: string, payload: { enabled: boolean; platformId: string; platformIp: string; port: string; password: string; resourcePath: string; autoRegister: boolean }) =>
    request<AccessGa1400Entry>(`/api/access-config/ga1400/entries/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteGa1400Entry: (id: string) =>
    request<void>(`/api/access-config/ga1400/entries/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  accessCertificates: () => request<AccessCertificate[]>('/api/access-config/certificates'),
  createAccessCertificate: (payload: { deviceCode: string; certificate: string; authMode: string }) =>
    request<AccessCertificate>('/api/access-config/certificates', { method: 'POST', body: JSON.stringify(payload) }),
  deleteAccessCertificate: (id: string) =>
    request<void>(`/api/access-config/certificates/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  accessHostIps: () => request<{ ips: string[] }>('/api/access-config/host-ip'),
  checkAccessPort: (port: number) =>
    request<{ port: number; available: boolean }>('/api/access-config/check-port', { method: 'POST', body: JSON.stringify({ port }) }),

  cloudPlatforms: () => request<CloudPlatform[]>('/api/cloud-platforms'),
  createCloudPlatform: (payload: CloudPlatformPayload) =>
    request<CloudPlatform>('/api/cloud-platforms', { method: 'POST', body: JSON.stringify(payload) }),
  updateCloudPlatform: (id: string, payload: CloudPlatformPayload) =>
    request<CloudPlatform>(`/api/cloud-platforms/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteCloudPlatform: (id: string) =>
    request<void>(`/api/cloud-platforms/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  cloudPlatformPrecheck: (id: string) =>
    request<CloudSyncPrecheck>(`/api/cloud-platforms/${encodeURIComponent(id)}/precheck`, { method: 'POST' }),
  cloudPlatformSync: (id: string, payload: { items: CloudDeviceItem[]; targetArea: string; overwrite: boolean }) =>
    request<CloudSyncResult>(`/api/cloud-platforms/${encodeURIComponent(id)}/sync`, { method: 'POST', body: JSON.stringify(payload) }),

  llmConfigs: () => request<LlmConfig[]>('/api/llm-configs'),
  createLlmConfig: (payload: LlmConfigPayload) =>
    request<LlmConfig>('/api/llm-configs', { method: 'POST', body: JSON.stringify(payload) }),
  updateLlmConfig: (id: string, payload: LlmConfigPayload) =>
    request<LlmConfig>(`/api/llm-configs/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteLlmConfig: (id: string) =>
    request<void>(`/api/llm-configs/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  testLlmConfig: (id: string) =>
    request<LlmTestResult>(`/api/llm-configs/${encodeURIComponent(id)}/test`, { method: 'POST' }),

  reviewTypes: () => request<ReviewType[]>('/api/review-types'),
  createReviewType: (payload: ReviewTypePayload) =>
    request<ReviewType>('/api/review-types', { method: 'POST', body: JSON.stringify(payload) }),
  updateReviewType: (id: string, payload: ReviewTypePayload) =>
    request<ReviewType>(`/api/review-types/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteReviewType: (id: string) =>
    request<void>(`/api/review-types/${encodeURIComponent(id)}`, { method: 'DELETE' }),

  reviewSchedules: () => request<ReviewSchedule[]>('/api/review-schedules'),
  createReviewSchedule: (payload: ReviewSchedulePayload) =>
    request<ReviewSchedule>('/api/review-schedules', { method: 'POST', body: JSON.stringify(payload) }),
  updateReviewSchedule: (id: string, payload: ReviewSchedulePayload) =>
    request<ReviewSchedule>(`/api/review-schedules/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteReviewSchedule: (id: string) =>
    request<{ deleted: string }>(`/api/review-schedules/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  runReviewSchedule: (id: string) =>
    request<{ started: string }>(`/api/review-schedules/${encodeURIComponent(id)}/run`, { method: 'POST' }),

  reviewTasks: () => request<ReviewTask[]>('/api/review-tasks'),
  createReviewTask: (form: FormData) => request<ReviewTask>('/api/review-tasks', { method: 'POST', body: form }),
  deleteReviewTask: (id: string) =>
    request<{ deleted: string }>(`/api/review-tasks/${encodeURIComponent(id)}`, { method: 'DELETE' }),

  eventInfos: () => request<EventInfo[]>('/api/event-infos'),
  createEventInfo: (payload: EventInfoPayload) =>
    request<EventInfo>('/api/event-infos', { method: 'POST', body: JSON.stringify(payload) }),
  updateEventInfo: (id: string, payload: EventInfoPayload) =>
    request<EventInfo>(`/api/event-infos/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteEventInfo: (id: string) =>
    request<void>(`/api/event-infos/${encodeURIComponent(id)}`, { method: 'DELETE' }),

  eventDedupRules: () => request<DedupRule[]>('/api/event-dedup-rules'),
  createEventDedupRule: (payload: DedupRulePayload) =>
    request<DedupRule>('/api/event-dedup-rules', { method: 'POST', body: JSON.stringify(payload) }),
  updateEventDedupRule: (id: string, payload: DedupRulePayload) =>
    request<DedupRule>(`/api/event-dedup-rules/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteEventDedupRule: (id: string) =>
    request<void>(`/api/event-dedup-rules/${encodeURIComponent(id)}`, { method: 'DELETE' }),

  eventPushTasks: () => request<PushTask[]>('/api/event-push-tasks'),
  createEventPushTask: (payload: PushTaskPayload) =>
    request<PushTask>('/api/event-push-tasks', { method: 'POST', body: JSON.stringify(payload) }),
  updateEventPushTask: (id: string, payload: PushTaskPayload) =>
    request<PushTask>(`/api/event-push-tasks/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteEventPushTask: (id: string) =>
    request<void>(`/api/event-push-tasks/${encodeURIComponent(id)}`, { method: 'DELETE' }),

  workerNodes: () => request<WorkerNode[]>('/api/worker-nodes'),
};

export function assetUrl(path?: string | null): string {
  if (!path) {
    return '';
  }
  if (path.startsWith('http')) {
    return path;
  }
  return `${baseUrlForPath(path)}${path}`;
}

// 文搜视频分析结果的真实截图：后端按时间点从视频文件截帧
export function videoAnalysisFrameUrl(videoUrl?: string | null, seconds = 0): string {
  if (!videoUrl) {
    return '';
  }
  const offset = Math.max(0, Math.floor(Number(seconds) || 0));
  return `${baseUrlForPath('/api/video-analysis/frame')}/api/video-analysis/frame?videoUrl=${encodeURIComponent(videoUrl)}&seconds=${offset}`;
}

export function streamUrl(path?: string | null): string | undefined {
  if (!path) {
    return undefined;
  }
  if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('blob:')) {
    return path;
  }
  const baseUrl = baseUrlForPath(path);
  if (path.startsWith('/')) {
    return `${baseUrl}${path}`;
  }
  return `${baseUrl}/${path}`;
}

export function cameraStreamUrl(camera?: Camera | null): string | undefined {
  if (!camera) {
    return undefined;
  }
  if (camera.objectDetectionEnabled) {
    return streamUrl(`/api/cameras/${camera.id}/annotated.mjpeg`);
  }
  if (camera.streamName && (camera.sourceUrl.startsWith('rtsp://') || camera.playbackUrl.includes('/live/'))) {
    return streamUrl(`/api/live/${encodeURIComponent(camera.streamName)}.live.flv`);
  }
  return streamUrl(camera.playbackUrl);
}

function resolveApiBaseUrl(configured?: string) {
  // 未显式配置时一律同源相对路径，由前端 nginx 反代到对应后端；
  // 禁止退回「浏览器本机:端口」——客户端直连后端端口在现网链路上可能被限速
  return configured ?? '';
}
