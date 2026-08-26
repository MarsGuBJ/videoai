export type Camera = {
  id: string;
  name: string;
  sourceUrl: string;
  streamApp: string;
  streamName: string;
  ffmpegKey?: string | null;
  description?: string | null;
  area?: string | null;
  status: string;
  playbackUrl: string;
  createdAt: string;
  updatedAt: string;
  nvrId?: string | null;
  nvrChannel?: string | null;
  nvrTrackId?: string | null;
  nvrStreamType?: string | null;
  objectDetectionEnabled?: boolean;
  protocol?: string | null;
  vendor?: string | null;
  ip?: string | null;
  port?: string | null;
  username?: string | null;
  password?: string | null;
  deviceCode?: string | null;
  serialNumber?: string | null;
};

export type CloudPlatform = {
  id: string;
  name: string;
  type: string;
  key: string;
  secret: string;
  ip: string;
  port: string;
  createdAt: string;
  updatedAt: string;
};

export type LlmConfig = {
  id: string;
  name: string;
  baseUrl: string;
  apiKey: string;
  apiKeyConfigured: boolean;
  deployType: 'cloud' | 'local';
  timeout: number;
  temperature: number;
  maxTokens: number;
  fps: number;
  createdAt: string;
  updatedAt: string;
};

export type LlmConfigPayload = {
  name: string;
  baseUrl: string;
  apiKey?: string;
  deployType: 'cloud' | 'local';
  timeout: number;
  temperature: number;
  maxTokens: number;
  fps: number;
};

export type LlmTestResult = {
  ok: boolean;
  latencyMs?: number;
  statusCode?: number;
  error?: string;
  checkedAt?: string;
};

export type EventInfoAttr = {
  key: string;
  value: string;
};

export type EventInfo = {
  id: string;
  name: string;
  code: string;
  level: string;
  category: string;
  mark: string;
  iconName: string;
  source: string;
  eventSource: string;
  algorithmCode: string;
  attrs: EventInfoAttr[];
  sortOrder: number;
  enabled: boolean;
  createdAt: string;
  updatedAt: string;
};

export type EventInfoPayload = {
  name: string;
  code: string;
  level: string;
  category: string;
  mark: string;
  iconName: string;
  source: string;
  eventSource: string;
  algorithmCode: string;
  attrs: EventInfoAttr[];
  sortOrder?: number;
  enabled: boolean;
};

export type DedupRule = {
  id: string;
  name: string;
  algorithm: string;
  strategy: string;
  durationMinutes?: number | null;
  similarity?: number | null;
  allCameras: boolean;
  cameras: string[];
  remark: string;
  enabled: boolean;
  createdAt: string;
  updatedAt: string;
};

export type DedupRulePayload = {
  name: string;
  algorithm: string;
  strategy: string;
  durationMinutes?: number | null;
  similarity?: number | null;
  allCameras: boolean;
  cameras: string[];
  remark: string;
  enabled: boolean;
};

export type PushTask = {
  id: string;
  name: string;
  type: 'mq' | 'http';
  address: string;
  mqAddr: string;
  mqUser: string;
  mqPass: string;
  mqPassConfigured: boolean;
  token: string;
  expireDays: number;
  eventSource: string;
  eventTypes: string;
  desc: string;
  enabled: boolean;
  createdAt: string;
  updatedAt: string;
};

export type PushTaskPayload = {
  name: string;
  type: 'mq' | 'http';
  address: string;
  mqAddr: string;
  mqUser: string;
  mqPass?: string;
  token: string;
  expireDays: number;
  eventSource: string;
  eventTypes: string;
  desc: string;
  enabled: boolean;
};

export type PtzCommand =
  | 'up'
  | 'down'
  | 'left'
  | 'right'
  | 'up_left'
  | 'up_right'
  | 'down_left'
  | 'down_right'
  | 'zoom_in'
  | 'zoom_out'
  | 'stop'
  | 'home'
  | 'preset_goto';

export type PtzCommandRequest = {
  command: PtzCommand;
  step?: number;
  preset?: number;
};

export type PtzCommandResponse = {
  cameraId: string;
  command: PtzCommand;
  channel: string;
  targetHost: string;
  ok: boolean;
};

export type FaceProfile = {
  id: string;
  name: string;
  description?: string | null;
  photoUrl: string;
  createdAt: string;
  updatedAt: string;
};

export type FaceEvent = {
  id: string;
  cameraId: string;
  faceProfileId: string;
  cameraName: string;
  profileName: string;
  profileDescription?: string | null;
  facePhotoUrl: string;
  snapshotUrl?: string | null;
  videoTime: string;
  similarity: number;
  createdAt: string;
};

export type ModelInfo = {
  id: string;
  name: string;
  displayName: string;
  repositoryPath?: string | null;
  modelType: string;
  description?: string | null;
  state: string;
  createdAt: string;
  updatedAt: string;
};

export type ModelGpuConfig = {
  modelName: string;
  gpuIds: number[];
  configPath: string;
};

export type WindowsCameraStatus = {
  available: boolean;
  running: boolean;
  ffmpegPath?: string | null;
  deviceName: string;
  streamName: string;
  publishUrl: string;
  devices: string[];
  message?: string | null;
};

export type FaceMatchEvent = {
  id: string;
  deploymentTaskId?: string | null;
  faceProfileId?: string | null;
  faceProfileName?: string | null;
  faceProfilePhotoUrl?: string | null;
  snapshotUrl?: string | null;
  cameraId?: string | null;
  cameraName?: string | null;
  cameraArea?: string | null;
  similarity?: number | null;
  matchedAt?: string | null;
  createdAt?: string | null;
};

export type DeploymentTask = {
  id: string;
  name: string;
  pipeline: string;
  area: string;
  areaCount: number;
  enabled: boolean;
  taskStatus: string;
  desc: string;
  faceProfileId?: string | null;
  faceProfileName?: string | null;
  faceProfilePhotoUrl?: string | null;
  cameraIds: string[];
  recognitionPerMinute: number;
  createdAt: string;
  updatedAt: string;
};

export type AccessGb28181Config = {
  enabled: boolean;
  sipId: string;
  sipDomain: string;
  sipIp: string;
  sipPort: string;
  password: string;
  parentPort: string;
  receivePortStart: string;
  receivePortEnd: string;
};

export type AccessGa1400Config = {
  enabled: boolean;
  platformId: string;
  platformIp: string;
  port: string;
  password: string;
  resourcePath: string;
  autoRegister: boolean;
};

export type AccessConfig = {
  gb28181?: AccessGb28181Config | null;
  ga1400?: AccessGa1400Config | null;
};

export type AccessCertificate = {
  id: string;
  deviceCode: string;
  certificate: string;
  authMode: string;
  createdAt: string;
  updatedAt: string;
};

export type DeploymentTaskCreate = {
  name?: string | null;
  pipeline?: string;
  area?: string | null;
  areaCount?: number;
  enabled?: boolean;
  desc?: string;
  faceProfileId?: string | null;
  faceProfileName?: string | null;
  faceProfilePhotoUrl?: string | null;
  cameraIds: string[];
  recognitionPerMinute?: number;
};
