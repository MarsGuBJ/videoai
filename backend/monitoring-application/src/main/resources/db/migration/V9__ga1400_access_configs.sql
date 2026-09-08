CREATE TABLE ga1400_access_configs (
    id UUID PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    platform_id VARCHAR(20) NOT NULL,
    platform_ip VARCHAR(64) NOT NULL,
    port VARCHAR(8) NOT NULL,
    password VARCHAR(128),
    resource_path VARCHAR(512),
    auto_register BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
