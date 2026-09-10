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
  videoPreviewEnabled?: boolean;
  audioEnabled?: boolean;
  talkbackEnabled?: boolean;
  ptzEnabled?: boolean;
  smartAnalysisEnabled?: boolean;
  alarmIoEnabled?: boolean;
  subStreamName?: string | null;
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
  model: string;
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
  model?: string;
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

export type ReviewType = {
  id: string;
  name: string;
  code: string;
  prompt: string;
  injectEvent: string;
  remark: string;
  llmConfigId?: string | null;
  createdAt: string;
  updatedAt: string;
};

export type ReviewSchedule = {
  id: string;
  name: string;
  cron: string;
  enabled: boolean;
  batchSize: number;
  reviewTypeId: string;
  reviewTypeName: string;
  reviewTypeCode: string;
  lastRunAt: string | null;
  lastResult: string;
  createdAt: string;
  updatedAt: string;
};

export type ReviewTask = {
  id: string;
  reviewTypeId: string;
  reviewTypeName: string;
  reviewTypeCode: string;
  llmConfigId: string;
  llmConfigName: string;
  imageUrl: string;
  status: string;
  verdict: string;
  reason: string;
  createdAt: string;
  updatedAt: string;
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

export type EventObjectInfo = {
  labelId: number;
  labelName: string;
  score: number;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
};

export type DeploymentEvent = {
  id: string;
  deploymentTaskId?: string | null;
  eventType: string;
  faceProfileId?: string | null;
  faceProfileName?: string | null;
  faceProfilePhotoUrl?: string | null;
  objects?: EventObjectInfo[] | null;
  frameWidth?: number;
  frameHeight?: number;
  snapshotUrl?: string | null;
  cameraId?: string | null;
  cameraName?: string | null;
  cameraArea?: string | null;
  similarity?: number | null;
  algorithmCode?: string | null;
  reviewStatus?: string | null;
  occurredAt: string;
  createdAt: string;
};

export type DeploymentEventPage = {
  items: DeploymentEvent[];
  total: number;
  page: number;
  size: number;
};

export type DeploymentEventSummary = {
  total: number;
  today: number;
  faceMatch: number;
  objectDetection: number;
};

export type DeploymentEventQuery = {
  page?: number;
  size?: number;
  taskId?: string;
  cameraId?: string;
  eventType?: string;
  keyword?: string;
  startTime?: string;
  endTime?: string;
};

export type DeploymentEventTrendItem = {
  date: string;
  count: number;
};

export type DeploymentEventAreaItem = {
  area: string;
  count: number;
};

export type DeploymentEventReviewItem = {
  eventType: string;
  valid: number;
  invalid: number;
  unreviewed: number;
};

export type DeploymentEventStats = {
  total: number;
  today: number;
  week: number;
  unreviewed: number;
  reviewRate: number;
  faceMatch: number;
  objectDetection: number;
  areas: string[];
  trend: DeploymentEventTrendItem[];
  byArea: DeploymentEventAreaItem[];
  reviewByType: DeploymentEventReviewItem[];
};

export type DeploymentEventStatsQuery = {
  startTime?: string;
  endTime?: string;
  area?: string;
};

export type AlgorithmEngine = {
  engineType: string;
  label: string;
  requiredFiles: string[];
  optionalFiles: string[];
  description?: string;
};

export type Algorithm = {
  id: string;
  name: string;
  code: string;
  engineType: string;
  engineLabel?: string;
  scene?: string | null;
  status: "RUNNING" | "DISABLED";
  owner?: string | null;
  description?: string | null;
  currentVersion?: string | null;
  versionCount: number;
  currentVersionStatus?: "READY" | "MISSING_FILES" | null;
  missingFiles: string[];
  createdAt: string;
  updatedAt: string;
};

export type AlgorithmVersion = {
  id: string;
  algorithmId: string;
  version: string;
  versionName?: string | null;
  notes?: string | null;
  status: "READY" | "MISSING_FILES";
  missingFiles: string[];
  fileManifest: Record<string, number>;
  active: boolean;
  createdAt: string;
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
  algorithmId?: string | null;
  algorithmName?: string | null;
  algorithmCode?: string | null;
  engineType?: string | null;
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

export type AccessGb28181Entry = {
  id: string;
  enabled: boolean;
  sipId: string;
  sipDomain: string;
  sipIp: string;
  sipPort: string;
  password: string;
  parentPort: string;
  receivePortStart: string;
  receivePortEnd: string;
  createdAt: string;
  updatedAt: string;
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

export type AccessGa1400Entry = {
  id: string;
  enabled: boolean;
  platformId: string;
  platformIp: string;
  port: string;
  password: string;
  resourcePath: string;
  autoRegister: boolean;
  createdAt: string;
  updatedAt: string;
};

export type AccessConfig = {
  gb28181?: AccessGb28181Config | null;
  ga1400?: AccessGa1400Config | null;
};

export type CloudDeviceItem = {
  name: string;
  area: string;
  protocol: string;
  ip: string;
  port: string;
  sourceUrl: string;
  status: "new" | "update" | null;
  localCameraId: string | null;
};

export type CloudSyncPrecheck = {
  items: CloudDeviceItem[];
  newCount: number;
  updateCount: number;
};

export type CloudSyncResult = {
  created: number;
  updated: number;
  skipped: number;
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
  algorithmId?: string | null;
  algorithmName?: string | null;
  algorithmCode?: string | null;
  engineType?: string | null;
  cameraIds: string[];
  recognitionPerMinute?: number;
};

export type GpuInfo = {
  index: number;
  name: string;
  status: '繁忙' | '空闲' | '离线';
  memoryTotalMb: number;
  memoryUsedMb: number;
  temperatureC: number;
  powerW: number;
  utilizationPct: number;
};

export type SystemMetrics = {
  cpuPercent: number;
  memoryTotalMb: number;
  memoryUsedMb: number;
  diskTotalGb: number;
  diskUsedGb: number;
};

export type WorkerNode = {
  id: string;
  hostname: string;
  ip: string;
  port: number;
  status: '在线' | '离线';
  lastSeenAt: string;
  gpus: GpuInfo[];
  system: SystemMetrics;
  createdAt: string;
  updatedAt: string;
};

export type SearchKeywordOut = {
  id: string;
  keyword: string;
  searchType: string;
  createdAt: string;
};

export type SearchKeywordStatItem = {
  keyword: string;
  searchType: string;
  count: number;
  lastSearchedAt: string;
};
