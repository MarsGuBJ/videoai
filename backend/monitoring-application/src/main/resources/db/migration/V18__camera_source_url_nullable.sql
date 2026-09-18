-- GB28181 云平台同步入库的设备无拉流地址：source_url 放宽为可空。
ALTER TABLE cameras ALTER COLUMN source_url DROP NOT NULL;
