CREATE TABLE gb28181_access_configs (
    id UUID PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    sip_id VARCHAR(20) NOT NULL,
    sip_domain VARCHAR(10) NOT NULL,
    sip_ip VARCHAR(64) NOT NULL,
    sip_port VARCHAR(8) NOT NULL,
    password VARCHAR(128),
    parent_port VARCHAR(8),
    receive_port_start VARCHAR(8),
    receive_port_end VARCHAR(8),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
