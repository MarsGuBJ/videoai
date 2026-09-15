<template>
  <section class="content review-wide">
    <div class="review-titlebar">
      <div><h1>设备详情</h1><p>查看设备基础信息、连接状态、能力与接入信息</p></div>
      <div class="segmented"><button class="btn" @click="setRoute('media')">返回设备管理</button><button class="btn primary" @click="editCurrent">编辑设备</button></div>
    </div>
    <div class="media-wall-config-grid" style="margin-top:0;">
      <section class="panel" style="padding:18px 22px;">
        <h3 class="form-section-title">设备类型</h3>
        <div class="event-detail-grid" style="grid-template-columns:1fr;gap:12px;margin-bottom:0;">
          <dl class="event-detail-field"><dt>设备类别</dt><dd>{{ camera.deviceCategory || '-' }}</dd></dl>
          <dl class="event-detail-field"><dt>设备类型</dt><dd>{{ camera.deviceType || '-' }}</dd></dl>
          <dl class="event-detail-field"><dt>厂商类型</dt><dd>{{ camera.vendor || '其他' }}</dd></dl>
        </div>
      </section>
      <section class="panel" style="padding:18px 22px;">
        <h3 class="form-section-title">通道信息</h3>
        <div class="event-detail-grid" style="grid-template-columns:1fr;gap:12px;margin-bottom:0;">
          <dl class="event-detail-field"><dt>通道号</dt><dd>{{ camera.nvrChannel || '-' }}</dd></dl>
          <dl class="event-detail-field"><dt>通道名称</dt><dd>{{ camera.channelName || '-' }}</dd></dl>
          <dl class="event-detail-field"><dt>码流类型</dt><dd>{{ camera.nvrStreamType || '-' }}</dd></dl>
        </div>
      </section>
    </div>
    <div class="panel" style="padding:18px 22px;margin-top:12px;">
      <h3 class="form-section-title">基本信息</h3>
      <div class="event-detail-grid" style="grid-template-columns:1fr 1fr;gap:12px;margin-bottom:0;">
        <dl class="event-detail-field"><dt>设备名称</dt><dd>{{ camera.name || '-' }}</dd></dl>
        <dl class="event-detail-field"><dt>设备编号</dt><dd>{{ camera.deviceCode || '-' }}</dd></dl>
        <dl class="event-detail-field"><dt>设备序列号</dt><dd>{{ camera.serialNumber || '-' }}</dd></dl>
        <dl class="event-detail-field"><dt>接入方式</dt><dd>{{ camera.protocol || '-' }}</dd></dl>
        <dl class="event-detail-field"><dt>协议版本</dt><dd>{{ camera.protocolVersion || '-' }}</dd></dl>
        <dl class="event-detail-field"><dt>IP地址及端口</dt><dd>{{ address }}</dd></dl>
        <dl class="event-detail-field"><dt>用户名</dt><dd>{{ camera.username || '-' }}</dd></dl>
        <dl class="event-detail-field"><dt>密码强度</dt><dd><span class="password-strength" :class="strength.cls">{{ strength.label }}</span></dd></dl>
        <dl class="event-detail-field"><dt>所属区域</dt><dd>{{ camera.area || '未分配' }}</dd></dl>
        <dl class="event-detail-field"><dt>设备能力</dt><dd>{{ capabilityText }}</dd></dl>
        <dl class="event-detail-field" style="grid-column:1 / -1;"><dt>描述</dt><dd>{{ camera.description || '-' }}</dd></dl>
      </div>
    </div>
    <div class="panel" style="padding:18px 22px;margin-top:12px;">
      <h3 class="form-section-title">高级配置</h3>
      <div class="event-detail-grid" style="grid-template-columns:1fr 1fr;gap:12px;margin-bottom:0;">
        <dl class="event-detail-field"><dt>拉流地址</dt><dd class="ellipsis">{{ camera.sourceUrl || '-' }}</dd></dl>
        <dl class="event-detail-field"><dt>回放地址</dt><dd class="ellipsis">{{ camera.playbackUrl || '-' }}</dd></dl>
        <dl class="event-detail-field"><dt>注册有效期</dt><dd>{{ registerExpireText }}</dd></dl>
        <dl class="event-detail-field"><dt>心跳周期</dt><dd>{{ heartbeatText }}</dd></dl>
        <dl class="event-detail-field"><dt>国标域编码</dt><dd>{{ camera.gbCode || '-' }}</dd></dl>
      </div>
    </div>
    <div class="panel" style="padding:18px 22px;margin-top:12px;">
      <h3 class="form-section-title">连接与状态</h3>
      <div class="event-detail-grid" style="grid-template-columns:1fr 1fr;gap:12px;margin-bottom:0;">
        <dl class="event-detail-field"><dt>连接状态</dt><dd><span class="status-pill" :class="statusClass(statusText)">{{ statusText }}</span></dd></dl>
        <dl class="event-detail-field"><dt>最近更新</dt><dd>{{ updatedAt }}</dd></dl>
        <dl class="event-detail-field"><dt>来源</dt><dd>手动添加</dd></dl>
        <dl class="event-detail-field"><dt>流应用 / 流名称</dt><dd>{{ streamInfo }}</dd></dl>
        <dl class="event-detail-field"><dt>NVR 标识</dt><dd>{{ camera.nvrId || '-' }}</dd></dl>
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api } from "../api";
import type { Camera } from "../types";
import { statusClass } from "../utils/prototype-helpers";
import { passwordStrength } from "../utils/regions";

function statusLabel(status?: string): string {
  const value = (status || "").toUpperCase();
  if (value === "RUNNING") return "在线";
  if (value === "STOPPED") return "离线";
  if (value === "DISABLED") return "停用";
  return "未成功连接";
}

function formatTime(value?: string): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

export default defineComponent({
  name: "MediaDeviceDetailPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm", "selectedCamera"],
  // Prototype declares `inject: ["setRoute"]`. The injected function is
  // aliased (setRouteImpl) and re-exposed as a method so the template's
  // `setRoute('...')` calls type-check under vue-tsc.
  inject: {
    setRouteImpl: { from: "setRoute", default: (_route: string, _options?: any) => {} },
    showToastImpl: { from: "showToast", default: (_m: string) => {} },
    openCameraEditImpl: { from: "openCameraEdit", default: (_row: any) => {} }
  },
  data() {
    return {
      camera: {} as Camera
    };
  },
  computed: {
    address(): string {
      if (this.camera.ip) return `${this.camera.ip}${this.camera.port ? `:${this.camera.port}` : ""}`;
      return "-";
    },
    strength(): { label: string; cls: string } {
      return passwordStrength(this.camera.password);
    },
    statusText(): string {
      return statusLabel(this.camera.status);
    },
    updatedAt(): string {
      return formatTime(this.camera.updatedAt);
    },
    streamInfo(): string {
      const app = this.camera.streamApp || "";
      const name = this.camera.streamName || "";
      if (!app && !name) return "-";
      return `${app || "-"}/${name || "-"}`;
    },
    // 与编辑页「设备能力」勾选项一致：视频/音频/云台/对讲/警告输入输出
    capabilityText(): string {
      const items: string[] = [];
      if (this.camera.videoPreviewEnabled) items.push("视频");
      if (this.camera.audioEnabled) items.push("音频");
      if (this.camera.ptzEnabled) items.push("云台");
      if (this.camera.talkbackEnabled) items.push("对讲");
      if (this.camera.alarmIoEnabled) items.push("警告输入输出");
      return items.length ? items.join("、") : "-";
    },
    registerExpireText(): string {
      return this.camera.registerExpire != null ? String(this.camera.registerExpire) : "-";
    },
    heartbeatText(): string {
      return this.camera.heartbeat != null ? String(this.camera.heartbeat) : "-";
    }
  },
  methods: {
    statusClass,
    setRoute(route: string, options?: any) {
      (this as any).setRouteImpl(route, options);
    },
    editCurrent() {
      if (!this.camera.id) return;
      (this as any).openCameraEditImpl(this.camera);
    }
  },
  async mounted() {
    const selected = this.selectedCamera as Camera | null;
    if (!selected) {
      (this as any).showToastImpl("请先选择设备");
      // 不能走 setRoute：它会同步修改 state.route，而 router-view :key 含 state.route，
      // 在 mounted 内同步触发本组件重挂载 → mounted 再次 setRoute，无限递归。
      this.$router.replace({ name: "media" }).catch(() => {});
      return;
    }
    this.camera = selected;
    try {
      const latest = await api.camera(selected.id);
      if (latest) this.camera = latest;
    } catch {
      // 拉取最新数据失败时保留列表传入的设备信息
    }
  }
});
</script>
