<template>
  <section class="content review-wide">
    <div class="review-titlebar">
      <div><h1>设备详情</h1><p>查看设备基础信息、连接状态、能力与通道信息</p></div>
      <div class="segmented"><button class="btn" @click="setRoute('media')">返回设备管理</button><button class="btn primary" @click="setRoute('mediaDeviceEdit')">编辑设备</button></div>
    </div>
    <div class="media-wall-config-grid" style="margin-top:0;">
      <section class="panel" style="padding:18px 22px;">
        <h3 class="form-section-title">基础信息</h3>
        <div class="event-detail-grid" style="grid-template-columns:1fr;gap:12px;margin-bottom:0;">
          <dl class="event-detail-field"><dt>设备名称</dt><dd>A1栋入口 IPC-01</dd></dl>
          <dl class="event-detail-field"><dt>所在区域</dt><dd>园区总部 / A区 / A1栋</dd></dl>
          <dl class="event-detail-field"><dt>接入协议</dt><dd>海康 SDK</dd></dl>
          <dl class="event-detail-field"><dt>IP地址及端口</dt><dd>192.168.96.70:8000</dd></dl>
          <dl class="event-detail-field"><dt>设备编号</dt><dd>100000000000000001</dd></dl>
          <dl class="event-detail-field"><dt>设备序列号</dt><dd>HK-6CD8-202607060001</dd></dl>
          <dl class="event-detail-field"><dt>密码强度</dt><dd><span class="password-strength medium">中</span></dd></dl>
          <dl class="event-detail-field"><dt>描述</dt><dd>主入口枪机，支持音频、云台和告警联动。</dd></dl>
        </div>
      </section>
      <section class="panel" style="padding:18px 22px;">
        <h3 class="form-section-title">连接与能力</h3>
        <div class="event-detail-grid" style="grid-template-columns:1fr;gap:12px;margin-bottom:0;">
          <dl class="event-detail-field"><dt>连接状态</dt><dd><span class="status-pill pass">在线</span></dd></dl>
          <dl class="event-detail-field"><dt>最近成功连接</dt><dd>2026-07-06 18:26:33</dd></dl>
          <dl class="event-detail-field"><dt>通道数量</dt><dd>2</dd></dl>
          <dl class="event-detail-field"><dt>设备能力</dt><dd>视频、音频、云台、告警输入、智能分析</dd></dl>
          <dl class="event-detail-field"><dt>来源</dt><dd>手动添加</dd></dl>
          <dl class="event-detail-field"><dt>厂商型号</dt><dd>海康威视 DS-2CD7A47E</dd></dl>
        </div>
      </section>
    </div>
    <div class="panel" style="padding:18px 22px;margin-top:12px;">
      <h3 class="form-section-title">通道信息</h3>
      <div class="modal-table-wrap" style="margin-bottom:0;">
        <table class="prototype-table">
          <thead><tr><th>通道号</th><th>通道名称</th><th>码流</th><th>能力</th><th>状态</th><th>联动告警</th></tr></thead>
          <tbody>
            <tr><td>1</td><td>A1栋入口通道</td><td>H.265 主码流</td><td>视频/音频</td><td><span class="status-pill pass">在线</span></td><td>门禁异常、区域入侵</td></tr>
            <tr><td>2</td><td>A1栋门禁联动</td><td>H.264 子码流</td><td>视频/云台</td><td><span class="status-pill reject">离线</span></td><td>门禁强开</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
  name: "MediaDeviceDetailPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  // Prototype declares `inject: ["setRoute"]`. The injected function is
  // aliased (setRouteImpl) and re-exposed as a method so the template's
  // `setRoute('...')` calls type-check under vue-tsc.
  inject: {
    setRouteImpl: { from: "setRoute", default: (_route: string, _options?: any) => {} },
  },
  methods: {
    setRoute(route: string, options?: any) {
      (this as any).setRouteImpl(route, options);
    },
  },
});
</script>
