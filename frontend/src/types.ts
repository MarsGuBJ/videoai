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
