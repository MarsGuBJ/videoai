import type { AccessCertificate, AccessConfig, AccessGa1400Config, AccessGb28181Config, Camera, CloudPlatform, DedupRule, DedupRulePayload, DeploymentTask, DeploymentTaskCreate, EventInfo, EventInfoPayload, FaceEvent, FaceMatchEvent, FaceProfile, LlmConfig, LlmConfigPayload, LlmTestResult, ModelGpuConfig, ModelInfo, PtzCommandRequest, PtzCommandResponse, PushTask, PushTaskPayload, WindowsCameraStatus } from '../types';

export type {
  AccessCertificate,
  AccessConfig,
  AccessGa1400Config,
  AccessGb28181Config,
  Camera,
  DeploymentTask,
  DeploymentTaskCreate,
  FaceEvent,
  FaceMatchEvent,
  FaceProfile,
  ModelGpuConfig,
  ModelInfo,
  PtzCommand,
  PtzCommandRequest,
  PtzCommandResponse,
  WindowsCameraStatus,
} from '../types';

export const API_BASE_URL = resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL);
export const MEDIA_API_BASE_URL = resolveApiBaseUrl(import.meta.env.VITE_MEDIA_API_BASE_URL, '8082');

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
};

type CloudPlatformPayload = {
  name?: string;
  type?: string;
  key?: string;
  secret?: string;
  ip?: string;
  port?: string;
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
    throw new Error(text || `${response.status} ${response.statusText}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  const text = await response.text();
  return text ? (JSON.parse(text) as T) : (undefined as T);
}

export const api = {
  cameras: () => request<Camera[]>('/api/cameras'),
  camera: (id: string) => request<Camera>(`/api/cameras/${id}`),
  createCamera: (payload: CameraPayload) =>
    request<Camera>('/api/cameras', { method: 'POST', body: JSON.stringify(payload) }),
  updateCamera: (id: string, payload: CameraPayload) =>
    request<Camera>(`/api/cameras/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteCamera: (id: string) => request<void>(`/api/cameras/${id}`, { method: 'DELETE' }),
  startCamera: (id: string) => request<Camera>(`/api/cameras/${id}/start`, { method: 'POST' }),
  stopCamera: (id: string) => request<Camera>(`/api/cameras/${id}/stop`, { method: 'POST' }),
  ptzControl: (id: string, payload: PtzCommandRequest) =>
    request<PtzCommandResponse>(`/api/cameras/${id}/ptz`, { method: 'POST', body: JSON.stringify(payload) }),

  faces: () => request<FaceProfile[]>('/api/faces'),
  createFace: (form: FormData) => request<FaceProfile>('/api/faces', { method: 'POST', body: form }),
  updateFace: (id: string, form: FormData) => request<FaceProfile>(`/api/faces/${id}`, { method: 'PATCH', body: form }),
  deleteFace: (id: string) => request<void>(`/api/faces/${id}`, { method: 'DELETE' }),

  events: () => request<FaceEvent[]>('/api/events?limit=100'),
  faceMatchEvents: (limit = 100) => request<FaceMatchEvent[]>(`/api/face-match-events?limit=${limit}`),

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

  accessConfig: () => request<AccessConfig>('/api/access-config'),
  saveGb28181Config: (payload: AccessGb28181Config) =>
    request<AccessGb28181Config>('/api/access-config/gb28181', { method: 'PUT', body: JSON.stringify(payload) }),
  saveGa1400Config: (payload: AccessGa1400Config) =>
    request<AccessGa1400Config>('/api/access-config/ga1400', { method: 'PUT', body: JSON.stringify(payload) }),
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

  llmConfigs: () => request<LlmConfig[]>('/api/llm-configs'),
  createLlmConfig: (payload: LlmConfigPayload) =>
    request<LlmConfig>('/api/llm-configs', { method: 'POST', body: JSON.stringify(payload) }),
  updateLlmConfig: (id: string, payload: LlmConfigPayload) =>
    request<LlmConfig>(`/api/llm-configs/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteLlmConfig: (id: string) =>
    request<void>(`/api/llm-configs/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  testLlmConfig: (id: string) =>
    request<LlmTestResult>(`/api/llm-configs/${encodeURIComponent(id)}/test`, { method: 'POST' }),

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

function resolveApiBaseUrl(configured?: string, defaultPort = '8081') {
  if (typeof window === 'undefined') {
    return configured ?? '';
  }
  if (configured) {
    return configured;
  }
  const localHosts = new Set(['localhost', '127.0.0.1', '::1']);
  if (localHosts.has(window.location.hostname)) {
    return `${window.location.protocol}//${window.location.hostname}:${defaultPort}`;
  }
  return '';
}
