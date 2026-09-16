<template>
  <section class="content review-wide device-edit-page">
    <div class="review-titlebar">
      <div><h1>编辑设备</h1><p>维护设备类型、基础参数、接入协议与通道信息</p></div>
      <div class="segmented"><button class="btn" @click="setRoute('mediaDeviceDetail')">返回设备详情</button></div>
    </div>
    <div class="panel form-panel" style="width:100%;">
      <h3 class="form-section-title">设备类型</h3>
      <div class="form-grid-3">
        <div class="wide-field-row"><label>设备类别：</label><select class="select" v-model="form.deviceCategory"><option>编码设备</option><option>解码设备</option></select></div>
        <div class="wide-field-row"><label>设备类型：</label><select class="select" v-model="form.deviceType"><option>IPC</option><option>NVR</option><option>DVR</option></select></div>
        <div class="wide-field-row"><label>厂商类型：</label><select class="select" v-model="form.vendor"><option>海康威视</option><option>大华</option><option>宇视</option><option>华为</option><option>其他</option></select></div>
      </div>
      <h3 class="form-section-title">基本信息</h3>
      <div class="form-grid-3">
        <div class="wide-field-row"><label>接入方式：</label><select class="select" v-model="form.protocol"><option>海康 SDK</option><option>GB28181</option><option>ONVIF</option><option>Ehome / ISUP 5.0</option><option>大华 SDK</option><option>RTSP 拉流</option><option>RTMP 推流</option><option>HTTP 拉流</option><option>GA/T 1400</option></select></div>
        <div class="wide-field-row"><label>协议版本：</label><select class="select" v-model="form.protocolVersion"><option>标准协议</option><option>海康 ISUP 5.0</option><option>GB/T 28181-2022</option><option>ONVIF Profile S</option></select></div>
        <div class="wide-field-row"><label>设备名称：</label><input class="input" v-model.trim="form.name" placeholder="请输入设备名称" /></div>
        <div class="wide-field-row"><label>设备编号：</label><input class="input" v-model.trim="form.deviceCode" placeholder="请输入设备编号" /></div>
        <div class="wide-field-row"><label>设备序列号：</label><input class="input" v-model.trim="form.serialNumber" placeholder="请输入设备序列号" /></div>
        <div class="wide-field-row"><label>拉流地址：</label><input class="input" v-model.trim="form.sourceUrl" placeholder="rtsp://user:pass@ip:port/stream" @input="onSourceUrlInput" @blur="probeSource" /></div>
        <div class="wide-field-row"><label>IP地址：</label><IpInput v-model="form.ip" /></div>
        <div class="wide-field-row"><label>端口号：</label><input class="input" v-model.trim="form.port" placeholder="554" /></div>
        <div class="wide-field-row"><label>用户名：</label><input class="input" v-model.trim="form.username" placeholder="admin" /></div>
        <div class="wide-field-row"><label>密码：</label><input class="input" type="password" v-model="form.password" placeholder="留空则不修改密码" /></div>
        <div class="wide-field-row"><label>所属区域：</label><select class="select" v-model="form.area"><option value="" disabled>请选择区域</option><option v-for="option in areaOptions" :key="option.fullPath" :value="option.fullPath">{{ option.label }}</option></select></div>
        <div class="wide-field-row"><label>设备能力：</label><span style="display:flex;gap:16px;flex-wrap:wrap;align-self:center;"><label class="video-device-include"><input type="checkbox" v-model="form.capabilityPtz" :disabled="ptzUnsupported" />云台控制</label></span></div>
      </div>
      <div class="wide-field-row"><label>描述：</label><textarea class="textarea" style="height:80px;" v-model.trim="form.description" placeholder="请输入设备描述"></textarea></div>
      <h3 class="form-section-title">高级配置</h3>
      <div class="form-grid-3">
        <div class="wide-field-row"><label>注册有效期：</label><input class="input" v-model.trim="form.registerExpire" placeholder="3600" /></div>
        <div class="wide-field-row"><label>心跳周期：</label><input class="input" v-model.trim="form.heartbeat" placeholder="60" /></div>
        <div class="wide-field-row"><label>国标域编码：</label><input class="input" v-model.trim="form.gbCode" placeholder="请输入 20 位国标编码" /></div>
      </div>
      <h3 class="form-section-title">通道信息</h3>
      <div class="form-grid-3">
        <div class="wide-field-row"><label>通道号：</label><input class="input" v-model.trim="form.nvrChannel" placeholder="1" /></div>
        <div class="wide-field-row"><label>通道名称：</label><input class="input" v-model.trim="form.channelName" placeholder="默认使用设备名称" /></div>
        <div class="wide-field-row"><label>码流类型：</label><select class="select" v-model="form.nvrStreamType"><option>主码流</option><option>子码流</option></select></div>
      </div>
      <div class="button-row"><button class="btn primary" :disabled="saving" @click="saveDevice">保存修改</button><button class="btn" @click="setRoute(cancelTarget)">取消</button></div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api } from "../api";
import IpInput from "../components/IpInput.vue";
import type { Camera } from "../types";
import { flattenRegionTree, hasSourceUrlCredentials, isValidChannelNo, isValidGbCode, isValidIPv4, isValidPort, loadRegionTree, MAX_CHANNEL_NO, normalizePath, parseSourceUrlParts } from "../utils/regions";
import type { FlatRegionNode } from "../utils/regions";

export default defineComponent({
  name: "MediaDeviceEditPage",
  components: { IpInput },
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm", "selectedCamera", "cameraEditOrigin"],
  inject: {
    setRoute: { from: "setRoute", default: (r: string, o?: any) => {} },
    showToast: { from: "showToast", default: (m: string) => {} },
    refreshCamerasImpl: { from: "refreshCameras", default: () => {} }
  },
  data() {
    return {
      saving: false,
      regionFlat: [] as FlatRegionNode[],
      // 云台能力探测：设备源不支持云台前禁用勾选框
      ptzUnsupported: false,
      sourceProbeTimer: null as ReturnType<typeof setTimeout> | null,
      lastProbedSource: "",
      form: {
        deviceCategory: "编码设备",
        deviceType: "IPC",
        vendor: "其他",
        protocol: "RTSP 拉流",
        protocolVersion: "标准协议",
        name: "",
        deviceCode: "",
        serialNumber: "",
        ip: "",
        port: "",
        username: "",
        password: "",
        area: "",
        description: "",
        sourceUrl: "",
        registerExpire: "3600",
        heartbeat: "60",
        gbCode: "",
        nvrChannel: "",
        channelName: "",
        nvrStreamType: "主码流",
        capabilityVideo: true,
        capabilityAudio: true,
        capabilityPtz: true,
        capabilityTalkback: false,
        capabilitySmartAnalysis: false,
        capabilityAlarmIo: false
      }
    };
  },
  computed: {
    // 取消时返回来源页：从设备详情进入则回详情，其余（设备管理表格）回表格页
    cancelTarget(): string {
      return this.cameraEditOrigin === "mediaDeviceDetail" ? "mediaDeviceDetail" : "media";
    },
    // 「所属区域」下拉与设备管理页「所在区域」同源：后端区域树按 sortOrder 展开，按层级缩进显示；
    // 当前设备区域不在树中时（如刚被改名前）追加到末尾，避免下拉丢值
    areaOptions(): { fullPath: string; label: string }[] {
      const options = this.regionFlat.map((item) => ({ fullPath: item.fullPath, label: "　".repeat(item.depth) + item.name }));
      if (this.form.area && !options.some((option) => option.fullPath === this.form.area)) {
        options.push({ fullPath: this.form.area, label: this.form.area });
      }
      return options;
    }
  },
  methods: {
    refreshCameras() {
      (this as any).refreshCamerasImpl();
    },
    // 拉流地址输入后：立即解析回填 IP/端口/用户名/密码，并延时触发设备源探测（序列号/云台能力）
    onSourceUrlInput() {
      const parts = parseSourceUrlParts(this.form.sourceUrl);
      if (parts.ip) this.form.ip = parts.ip;
      if (parts.port) this.form.port = parts.port;
      if (parts.username) this.form.username = parts.username;
      if (parts.password) this.form.password = parts.password;
      if (this.sourceProbeTimer) clearTimeout(this.sourceProbeTimer);
      this.sourceProbeTimer = setTimeout(() => this.probeSource(), 800);
    },
    async probeSource() {
      const sourceUrl = (this.form.sourceUrl || "").trim();
      if (!sourceUrl || sourceUrl === this.lastProbedSource || !hasSourceUrlCredentials(sourceUrl)) return;
      this.lastProbedSource = sourceUrl;
      try {
        const result = await api.probeCameraSource(sourceUrl);
        if ((this.form.sourceUrl || "").trim() !== sourceUrl) return; // 等待期间地址已被修改
        if (!result.reachable) return;
        if (result.serialNumber) this.form.serialNumber = result.serialNumber;
        if (result.ptzSupported === true) {
          this.form.capabilityPtz = true;
          this.ptzUnsupported = false;
        } else if (result.ptzSupported === false) {
          this.form.capabilityPtz = false;
          this.ptzUnsupported = true;
        }
      } catch {
        // 探测失败静默：不阻塞表单填写
      }
    },
    fillForm(camera: Camera) {
      this.form.name = camera.name || "";
      this.form.deviceCode = camera.deviceCode || "";
      this.form.serialNumber = camera.serialNumber || "";
      this.form.protocol = camera.protocol || "RTSP 拉流";
      this.form.ip = camera.ip || "";
      this.form.port = camera.port || "";
      this.form.area = normalizePath(camera.area);
      this.form.username = camera.username || "";
      this.form.password = "";
      this.form.vendor = camera.vendor || "其他";
      this.form.sourceUrl = camera.sourceUrl || "";
      this.form.description = camera.description || "";
      this.form.nvrChannel = camera.nvrChannel || "";
      this.form.nvrStreamType = camera.nvrStreamType || "主码流";
      this.form.capabilityVideo = !!camera.videoPreviewEnabled;
      this.form.capabilityAudio = !!camera.audioEnabled;
      this.form.capabilityPtz = !!camera.ptzEnabled;
      this.form.capabilityTalkback = !!camera.talkbackEnabled;
      this.form.capabilitySmartAnalysis = !!camera.smartAnalysisEnabled;
      this.form.capabilityAlarmIo = !!camera.alarmIoEnabled;
      this.form.deviceCategory = camera.deviceCategory || "编码设备";
      this.form.deviceType = camera.deviceType || "IPC";
      this.form.protocolVersion = camera.protocolVersion || "标准协议";
      this.form.registerExpire = camera.registerExpire != null ? String(camera.registerExpire) : "3600";
      this.form.heartbeat = camera.heartbeat != null ? String(camera.heartbeat) : "60";
      this.form.gbCode = camera.gbCode || "";
      this.form.channelName = camera.channelName || "";
    },
    async saveDevice() {
      if (this.saving) return;
      const camera = this.selectedCamera as Camera | null;
      if (!camera) return;
      if (!this.form.name.trim()) {
        (this as any).showToast("请填写设备名称");
        return;
      }
      if (this.form.ip.trim() && !isValidIPv4(this.form.ip)) {
        (this as any).showToast("IP地址格式不正确");
        return;
      }
      if (this.form.port.trim() && !isValidPort(this.form.port)) {
        (this as any).showToast("端口号必须为1-65535的整数");
        return;
      }
      if (this.form.nvrChannel.trim() && !isValidChannelNo(this.form.nvrChannel)) {
        (this as any).showToast(`通道号必须为1-${MAX_CHANNEL_NO}的整数`);
        return;
      }
      if (this.form.gbCode.trim() && !isValidGbCode(this.form.gbCode)) {
        (this as any).showToast("国标域编码必须为20位数字");
        return;
      }
      const payload: any = {
        name: this.form.name.trim(),
        sourceUrl: this.form.sourceUrl || undefined,
        description: this.form.description || undefined,
        area: this.form.area || undefined,
        protocol: this.form.protocol || undefined,
        vendor: this.form.vendor || undefined,
        ip: this.form.ip || undefined,
        port: this.form.port || undefined,
        username: this.form.username || undefined,
        deviceCode: this.form.deviceCode || undefined,
        serialNumber: this.form.serialNumber || undefined,
        nvrChannel: this.form.nvrChannel || undefined,
        nvrStreamType: this.form.nvrStreamType || undefined,
        videoPreviewEnabled: this.form.capabilityVideo,
        audioEnabled: this.form.capabilityAudio,
        ptzEnabled: this.form.capabilityPtz,
        talkbackEnabled: this.form.capabilityTalkback,
        smartAnalysisEnabled: this.form.capabilitySmartAnalysis,
        alarmIoEnabled: this.form.capabilityAlarmIo
      };
      // 新扩展字段：文本空串视为未填写；注册有效期/心跳周期解析为整数
      payload.deviceCategory = this.form.deviceCategory || undefined;
      payload.deviceType = this.form.deviceType || undefined;
      payload.protocolVersion = this.form.protocolVersion || undefined;
      payload.gbCode = this.form.gbCode || undefined;
      payload.channelName = this.form.channelName || undefined;
      const registerExpire = this.form.registerExpire.trim();
      if (registerExpire) {
        const parsed = parseInt(registerExpire, 10);
        if (Number.isNaN(parsed)) {
          (this as any).showToast("注册有效期必须为整数");
          return;
        }
        payload.registerExpire = parsed;
      }
      const heartbeat = this.form.heartbeat.trim();
      if (heartbeat) {
        const parsed = parseInt(heartbeat, 10);
        if (Number.isNaN(parsed)) {
          (this as any).showToast("心跳周期必须为整数");
          return;
        }
        payload.heartbeat = parsed;
      }
      if (this.form.password) payload.password = this.form.password;
      this.saving = true;
      try {
        await api.updateCamera(camera.id, payload);
        (this as any).showToast("设备信息已保存");
        this.refreshCameras();
        (this as any).setRoute("mediaDeviceDetail");
      } catch (error: any) {
        (this as any).showToast(`设备保存失败：${error?.message || error}`);
      } finally {
        this.saving = false;
      }
    }
  },
  async mounted() {
    const camera = this.selectedCamera as Camera | null;
    if (!camera) {
      (this as any).showToast("请先选择设备");
      // 同 MediaDeviceDetailPage：mounted 内不能用 setRoute（router-view :key 递归重挂载）
      this.$router.replace({ name: "media" }).catch(() => {});
      return;
    }
    this.fillForm(camera);
    try {
      const latest = await api.camera(camera.id);
      if (latest) this.fillForm(latest);
    } catch {
      // 拉取最新数据失败时保留列表传入的设备信息
    }
    try {
      // 「所属区域」下拉与设备管理页「所在区域」同源，来自后端区域树
      this.regionFlat = flattenRegionTree(await loadRegionTree());
    } catch {
      // 区域列表加载失败时保留下拉为空
    }
  }
});
</script>
