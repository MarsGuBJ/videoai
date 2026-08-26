-- 兼容历史库：backend-lite 时代已存在的 cameras 表缺少 V1 的 ffmpeg_key 列
ALTER TABLE cameras
    ADD COLUMN IF NOT EXISTS ffmpeg_key TEXT;
