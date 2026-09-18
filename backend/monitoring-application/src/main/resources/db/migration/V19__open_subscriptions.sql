-- 对外开放的设备变更订阅表：第三方注册回调地址后，
-- 设备基础信息变化（新增/编辑/删除）与在线状态变化时向 callback_url 推送。
CREATE TABLE IF NOT EXISTS open_subscriptions (
    id          UUID PRIMARY KEY,
    name        VARCHAR(128),
    callback_url TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
