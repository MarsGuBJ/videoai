import type { Camera, DeploymentTask, DeploymentTaskCreate, FaceEvent, FaceMatchEvent, FaceProfile, ModelGpuConfig, ModelInfo, PtzCommandRequest, PtzCommandResponse, WindowsCameraStatus } from './types';

export const API_BASE_URL = resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL);

type CameraPayload = {
  name: string;
  sourceUrl: string;
  description?: string;
  area?: string;
  nvrId?: string;
  nvrChannel?: string;
  nvrTrackId?: string;
  nvrStreamType?: string;
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

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
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
};

export function assetUrl(path?: string | null): string {
  if (!path) {
    return '';
  }
  if (path.startsWith('http')) {
    return path;
  }
  return `${API_BASE_URL}${path}`;
}

export function streamUrl(path?: string | null): string | undefined {
  if (!path) {
    return undefined;
  }
  if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('blob:')) {
    return path;
  }
  if (path.startsWith('/')) {
    return `${API_BASE_URL}${path}`;
  }
  return `${API_BASE_URL}/${path}`;
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
  if (typeof window === 'undefined') {
    return configured ?? '';
  }
  if (configured) {
    return configured;
  }
  const localHosts = new Set(['localhost', '127.0.0.1', '::1']);
  if (localHosts.has(window.location.hostname)) {
    return `${window.location.protocol}//${window.location.hostname}:8081`;
  }
  return '';
}
