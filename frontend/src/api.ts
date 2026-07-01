import type { Camera, FaceEvent, FaceProfile, ModelInfo, WindowsCameraStatus } from './types';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? defaultApiBaseUrl();

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
  createCamera: (payload: { name: string; sourceUrl: string; description?: string; nvrId?: string; nvrChannel?: string; nvrTrackId?: string; nvrStreamType?: string }) =>
    request<Camera>('/api/cameras', { method: 'POST', body: JSON.stringify(payload) }),
  updateCamera: (id: string, payload: { name: string; sourceUrl: string; description?: string; nvrId?: string; nvrChannel?: string; nvrTrackId?: string; nvrStreamType?: string }) =>
    request<Camera>(`/api/cameras/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteCamera: (id: string) => request<void>(`/api/cameras/${id}`, { method: 'DELETE' }),
  startCamera: (id: string) => request<Camera>(`/api/cameras/${id}/start`, { method: 'POST' }),
  stopCamera: (id: string) => request<Camera>(`/api/cameras/${id}/stop`, { method: 'POST' }),

  faces: () => request<FaceProfile[]>('/api/faces'),
  createFace: (form: FormData) => request<FaceProfile>('/api/faces', { method: 'POST', body: form }),
  updateFace: (id: string, form: FormData) => request<FaceProfile>(`/api/faces/${id}`, { method: 'PATCH', body: form }),
  deleteFace: (id: string) => request<void>(`/api/faces/${id}`, { method: 'DELETE' }),

  events: () => request<FaceEvent[]>('/api/events?limit=100'),

  models: () => request<ModelInfo[]>('/api/models'),
  registerModel: (payload: { name: string; displayName: string; repositoryPath?: string; modelType: string; description?: string }) =>
    request<ModelInfo>('/api/models/register', { method: 'POST', body: JSON.stringify(payload) }),
  loadModel: (name: string) => request<ModelInfo>(`/api/models/${name}/load`, { method: 'POST' }),
  unloadModel: (name: string) => request<ModelInfo>(`/api/models/${name}/unload`, { method: 'POST' }),
  modelConfig: (name: string) => request<{ name: string; config: Record<string, unknown> }>(`/api/models/${name}/config`),

  windowsCameraStatus: () => request<WindowsCameraStatus>('/api/windows-camera/status'),
  startWindowsCamera: (payload?: { deviceName?: string; streamName?: string }) =>
    request<WindowsCameraStatus>('/api/windows-camera/start', { method: 'POST', body: JSON.stringify(payload ?? {}) }),
  stopWindowsCamera: () => request<WindowsCameraStatus>('/api/windows-camera/stop', { method: 'POST' }),
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
  if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('blob:') || path.startsWith('/')) {
    return path;
  }
  return `${API_BASE_URL}/${path}`;
}

function defaultApiBaseUrl() {
  if (typeof window === 'undefined') {
    return 'http://localhost:8081';
  }
  return `${window.location.protocol}//${window.location.hostname}:8081`;
}
