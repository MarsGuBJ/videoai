CREATE TABLE IF NOT EXISTS cameras (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    stream_app TEXT NOT NULL,
    stream_name TEXT NOT NULL,
    ffmpeg_key TEXT,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'STOPPED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS face_profiles (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    photo_path TEXT NOT NULL,
    embedding TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS face_events (
    id UUID PRIMARY KEY,
    camera_id UUID NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
    face_profile_id UUID NOT NULL REFERENCES face_profiles(id) ON DELETE CASCADE,
    camera_name TEXT NOT NULL,
    profile_name TEXT NOT NULL,
    profile_description TEXT,
    face_photo_path TEXT NOT NULL,
    snapshot_path TEXT,
    video_time TIMESTAMPTZ NOT NULL,
    similarity DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS face_events_created_at_idx ON face_events (created_at DESC);
CREATE INDEX IF NOT EXISTS face_events_camera_profile_idx ON face_events (camera_id, face_profile_id, created_at DESC);

CREATE TABLE IF NOT EXISTS model_registry (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    repository_path TEXT,
    model_type TEXT NOT NULL,
    description TEXT,
    state TEXT NOT NULL DEFAULT 'UNKNOWN',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO model_registry (id, name, display_name, repository_path, model_type, description, state)
VALUES
    ('00000000-0000-0000-0000-000000000101', 'scrfd_10g', 'SCRFD-10GF', '/models/scrfd_10g', 'FACE_DETECTION', 'InsightFace SCRFD-10GF face detector and 5-point landmark model', 'UNKNOWN'),
    ('00000000-0000-0000-0000-000000000102', 'arcface_r50', 'ArcFace R50', '/models/arcface_r50', 'FACE_RECOGNITION', 'InsightFace ArcFace R50 face embedding model', 'UNKNOWN'),
    ('00000000-0000-0000-0000-000000000103', 'arcface_mbf', 'ArcFace MobileFaceNet', '/models/arcface_mbf', 'FACE_RECOGNITION', 'InsightFace buffalo_s MobileFaceNet embedding model, w600k_mbf.onnx, about 13 MB', 'UNKNOWN')
ON CONFLICT (name) DO NOTHING;
