CREATE TABLE access_config (
    protocol TEXT PRIMARY KEY,
    config JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE device_certificates (
    id UUID PRIMARY KEY,
    device_code VARCHAR(20) NOT NULL,
    certificate TEXT NOT NULL,
    auth_mode VARCHAR(8) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
