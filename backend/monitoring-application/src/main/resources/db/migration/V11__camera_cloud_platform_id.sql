-- 缺陷修复 TC-YPT-007：cameras 记录来源云平台（可空引用 cloud_platforms.id，不加外键约束，
-- 删除保护由 CloudPlatformServiceImpl 在 Service 层做引用计数拦截）。
ALTER TABLE cameras ADD COLUMN IF NOT EXISTS cloud_platform_id UUID;
