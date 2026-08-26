package com.videoai.monitoring.core.dao;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.videoai.monitoring.core.entity.DeviceCertificateEntity;

import java.util.List;

public interface DeviceCertificateDao extends BaseMapper<DeviceCertificateEntity> {

    List<DeviceCertificateEntity> selectAllOrdered();
}
