-- 兼容历史库：backend-lite 时代的 cameras.playback_url 为 NOT NULL，新架构播放地址由后端动态生成、不再落库。
-- 保留列（防回滚），仅放宽约束并给默认值，避免 INSERT 未提供该列时违反非空约束。
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'cameras' AND column_name = 'playback_url'
    ) THEN
        ALTER TABLE cameras ALTER COLUMN playback_url DROP NOT NULL;
        ALTER TABLE cameras ALTER COLUMN playback_url SET DEFAULT '';
    END IF;
END $$;
