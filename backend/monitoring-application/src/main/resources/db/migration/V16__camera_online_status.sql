-- 设备在线状态与拉流状态分离：
--   status        只表达"拉流状态"（RUNNING 拉流中 / STOPPED 已停止 / DISABLED 停用）
--   online_status 表达"设备可达性"（ONLINE 可达 / OFFLINE 不可达 / UNKNOWN 未探测）
-- 历史 OFFLINE 表示"拉流中但设备探测不可达"：拉流意图保留为 RUNNING，可达性迁移到新字段，
-- 这样 10 分钟一次的状态扫描对全部设备（含 STOPPED/DISABLED）都写 online_status，不再改动拉流状态。
ALTER TABLE cameras
    ADD COLUMN IF NOT EXISTS online_status VARCHAR(16) NOT NULL DEFAULT 'UNKNOWN';

UPDATE cameras
SET online_status = 'OFFLINE',
    status = 'RUNNING'
WHERE status = 'OFFLINE';
