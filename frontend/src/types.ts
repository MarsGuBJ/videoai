export type Camera = {
  id: string;
  name: string;
  sourceUrl: string;
  streamApp: string;
  streamName: string;
  ffmpegKey?: string | null;
  description?: string | null;
  status: string;
  playbackUrl: string;
  createdAt: string;
  updatedAt: string;
  nvrId?: string | null;
  nvrChannel?: string | null;
  nvrTrackId?: string | null;
  nvrStreamType?: string | null;
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
