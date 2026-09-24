-- 空间服务（spatialServer）配置：设备管理页「区域管理 → 同步空间区域」读取空间树的基址。
-- 单行配置（id 固定 1），可在界面修改；接口不可达时同步只记日志不报错。
CREATE TABLE IF NOT EXISTS spatial_config (
    id SMALLINT PRIMARY KEY,
    base_url TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO spatial_config (id, base_url)
VALUES (1, 'http://172.17.2.131:8080')
ON CONFLICT (id) DO NOTHING;
