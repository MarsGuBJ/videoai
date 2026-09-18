-- GB28181 接入配置条目改造为级联服务器模型：名称/IP/端口/用户名/密码。
-- 新增 username 列；sip_id/sip_domain 放宽为可空（遗留列保留，新代码不再写入）。
ALTER TABLE gb28181_access_configs ADD COLUMN IF NOT EXISTS username VARCHAR(64);
ALTER TABLE gb28181_access_configs ALTER COLUMN sip_id DROP NOT NULL;
ALTER TABLE gb28181_access_configs ALTER COLUMN sip_domain DROP NOT NULL;
