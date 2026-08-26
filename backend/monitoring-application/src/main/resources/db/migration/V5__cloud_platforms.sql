CREATE TABLE cloud_platforms (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    key TEXT NOT NULL,
    secret TEXT NOT NULL,
    ip TEXT NOT NULL,
    port TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
