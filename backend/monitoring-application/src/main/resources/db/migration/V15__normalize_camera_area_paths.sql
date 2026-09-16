-- 统一 cameras.area 路径分隔符为 " / "（如 赛迪电气/园区 -> 赛迪电气 / 园区），
-- 与区域树节点完整路径口径一致，保证区域设备计数与重命名前缀替换能够匹配。
-- 幂等：已规范化的值执行后不变。
UPDATE cameras
SET area = (
    SELECT string_agg(trim(part), ' / ')
    FROM unnest(string_to_array(area, '/')) AS part
    WHERE trim(part) <> ''
)
WHERE area IS NOT NULL AND btrim(area) <> '';
