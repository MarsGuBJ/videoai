<template>
  <section class="content review-wide device-wizard-page">
    <div class="review-titlebar">
      <div><h1>新增设备</h1><p>按设备类型、接入协议和通道信息完成编码设备接入</p></div>
      <div class="segmented"><button class="btn" @click="setRoute('media')">返回设备管理</button></div>
    </div>
    <div class="media-resource-tabs">
      <button :class="{ active: wizardStep === 1 }" @click="wizardStep = 1"><span class="step-badge">1</span> 选择设备类型</button>
      <button :class="{ active: wizardStep === 2 }" @click="wizardStep = 2"><span class="step-badge">2</span> 配置基本信息</button>
      <button :class="{ active: wizardStep === 3 }" @click="wizardStep = 3"><span class="step-badge">3</span> 配置通道信息</button>
    </div>
    <div v-if="wizardStep === 1" class="panel form-panel" style="width:100%;">
      <h3 class="form-section-title">设备类型</h3>
      <div class="form-grid-3">
        <div class="wide-field-row"><label><span class="required">*</span>设备类别：</label><select class="select" v-model="form.deviceCategory"><option>编码设备</option><option>解码设备</option></select></div>
        <div class="wide-field-row"><label><span class="required">*</span>设备类型：</label><select class="select" v-model="form.deviceType"><option>IPC</option><option>NVR</option><option>DVR</option></select></div>
        <div class="wide-field-row"><label><span class="required">*</span>厂商类型：</label><select class="select" v-model="form.vendor"><option>海康威视</option><option>大华</option><option>宇视</option><option>华为</option><option>其他厂商</option></select></div>
      </div>
      <div class="button-row"><button class="btn primary" @click="wizardStep = 2">下一步</button><button class="btn" @click="setRoute('media')">取消</button></div>
    </div>
    <div v-else-if="wizardStep === 2" class="panel form-panel" style="width:100%;">
      <div class="modal-summary-strip"><span>设备类别：{{ form.deviceCategory }}</span><span>设备类型：{{ form.deviceType }}</span><span>厂商类型：{{ form.vendor }}</span></div>
      <h3 class="form-section-title">基本信息</h3>
      <div class="form-grid-3">
        <div class="wide-field-row"><label><span class="required">*</span>接入方式：</label><select class="select" v-model="form.protocol"><option>海康 SDK</option><option>GB28181</option><option>ONVIF</option><option>Ehome / ISUP 5.0</option><option>大华 SDK</option><option>RTSP 拉流</option><option>RTMP 推流</option><option>HTTP 拉流</option><option>GA/T 1400</option></select></div>
        <div class="wide-field-row"><label><span class="required">*</span>协议版本：</label><select class="select" v-model="form.protocolVersion"><option>标准协议</option><option>海康 ISUP 5.0</option><option>GB/T 28181-2022</option><option>ONVIF Profile S</option></select></div>
        <div class="wide-field-row"><label><span class="required">*</span>设备名称：</label><input class="input" v-model.trim="form.name" placeholder="请输入设备名称" /></div>
        <div class="wide-field-row"><label><span class="required">*</span>拉流地址：</label><input class="input" v-model.trim="form.sourceUrl" placeholder="rtsp://user:pass@ip:port/stream" @input="onSourceUrlInput" @blur="probeSource" /></div>
        <div class="wide-field-row"><label><span class="required">*</span>IP地址：</label><IpInput v-model="form.ip" /></div>
        <div class="wide-field-row"><label><span class="required">*</span>端口号：</label><input class="input" v-model.trim="form.port" placeholder="554" /></div>
        <div class="wide-field-row"><label>用户名：</label><input class="input" v-model.trim="form.username" placeholder="admin" /></div>
        <div class="wide-field-row"><label>密码：</label><input class="input" type="password" v-model="form.password" placeholder="请输入设备密码" /></div>
        <div class="wide-field-row"><label><span class="required">*</span>所属区域：</label><select class="select" v-model="form.area"><option value="" disabled>请选择区域</option><option v-for="option in areaOptions" :key="option.fullPath" :value="option.fullPath">{{ option.label }}</option></select></div>
        <div class="wide-field-row"><label>设备能力：</label><span style="display:flex;gap:16px;flex-wrap:wrap;align-self:center;"><label class="video-device-include"><input type="checkbox" v-model="form.capabilityPtz" :disabled="ptzUnsupported" />云台控制</label></span></div>
      </div>
      <div class="wide-field-row"><label>描述：</label><textarea class="textarea" style="height:80px;" v-model.trim="form.description" placeholder="请输入设备描述"></textarea></div>
      <h3 class="form-section-title">高级配置</h3>
      <div class="form-grid-3">
        <div class="wide-field-row"><label><span class="required">*</span>注册有效期：</label><input class="input" v-model.trim="form.registerExpire" placeholder="3600" /></div>
        <div class="wide-field-row"><label><span class="required">*</span>心跳周期：</label><input class="input" v-model.trim="form.heartbeat" placeholder="60" /></div>
        <div class="wide-field-row"><label><span class="required">*</span>国标域编码：</label><input class="input" v-model.trim="form.gbCode" placeholder="请输入 20 位国标编码" /></div>
      </div>
      <div class="button-row"><button class="btn" @click="wizardStep = 1">上一步</button><button class="btn primary" @click="wizardStep = 3">下一步</button><button class="btn" @click="setRoute('media')">取消</button></div>
    </div>
    <div v-else class="panel form-panel" style="width:100%;">
      <h3 class="form-section-title">通道信息</h3>
      <p class="modal-hint">当前版本每台设备接入一个通道。</p>
      <div class="form-grid-3">
        <div class="wide-field-row"><label><span class="required">*</span>通道号：</label><input class="input" v-model.trim="form.nvrChannel" placeholder="1" /></div>
        <div class="wide-field-row"><label><span class="required">*</span>通道名称：</label><input class="input" v-model.trim="form.channelName" placeholder="默认使用设备名称" /></div>
        <div class="wide-field-row"><label><span class="required">*</span>码流类型：</label><select class="select" v-model="form.nvrStreamType"><option>主码流</option><option>子码流</option></select></div>
      </div>
      <div class="button-row" style="margin-top:14px;"><button class="btn" @click="wizardStep = 2">上一步</button><button class="btn primary" :disabled="saving" @click="finishWizard">保存</button><button class="btn" @click="setRoute('media')">取消</button></div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api } from "../api";
import IpInput from "../components/IpInput.vue";
import { computeSourceUrl, flattenRegionTree, hasSourceUrlCredentials, isValidChannelNo, isValidGbCode, isValidIPv4, isValidPort, loadRegionTree, MAX_CHANNEL_NO, parseSourceUrlParts } from "../utils/regions";
import type { FlatRegionNode } from "../utils/regions";

export default defineComponent({
  name: "MediaDeviceWizardPage",
  components: { IpInput },
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm", "selectedCamera"],
  // Aliased injection + same-named method wrappers so the template type-checks;
  // runtime behavior matches the prototype's `inject: ["setRoute", "showToast"]`.
  inject: {
    setRouteImpl: { from: "setRoute" },
    showToastImpl: { from: "showToast" },
    refreshCamerasImpl: { from: "refreshCameras", default: () => {} }
  },
  data() {
    return {
      wizardStep: 1,
      saving: false,
      regionFlat: [] as FlatRegionNode[],
      // 云台能力探测：设备源不支持云台前禁用勾选框
      ptzUnsupported: false,
      sourceProbeTimer: null as ReturnType<typeof setTimeout> | null,
      lastProbedSource: "",
      form: {
        deviceCategory: "编码设备",
        deviceType: "IPC",
        vendor: "海康威视",
        protocol: "RTSP 拉流",
        protocolVersion: "标准协议",
        name: "",
        // 序列号由拉流地址探测/后端创建后回取，页面不再手填
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
        nvrChannel: "1",
        channelName: "",
        nvrStreamType: "主码流",
        // 设备能力勾选与批量配置弹窗/编辑页同一组字段，默认值沿用原静态勾选状态
        capabilityVideo: true,
        capabilityAudio: true,
        capabilityTalkback: false,
        capabilityPtz: true,
        capabilitySmartAnalysis: false,
        capabilityAlarmIo: false
      }
    };
  },
  computed: {
    // 「所属区域」下拉与设备管理页「所在区域」同源：后端区域树按 sortOrder 展开，按层级缩进显示
    areaOptions(): { fullPath: string; label: string }[] {
      return this.regionFlat.map((item) => ({ fullPath: item.fullPath, label: "　".repeat(item.depth) + item.name }));
    }
  },
  methods: {
    setRoute(route: string, options?: any) {
      (this as any).setRouteImpl(route, options);
    },
    showToast(msg: string) {
      (this as any).showToastImpl(msg);
    },
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
    async finishWizard() {
      if (this.saving) return;
      const form = this.form;
      // 除用户名/密码/描述外均为必填：先校验第 2 步基本信息与高级配置，再校验第 3 步通道信息
      const failStep2 = (msg: string) => {
        this.showToast(msg);
        this.wizardStep = 2;
      };
      if (!form.name.trim()) return failStep2("请填写设备名称");
      if (!form.ip.trim()) return failStep2("请填写IP地址");
      if (!isValidIPv4(form.ip)) return failStep2("IP地址格式不正确");
      if (!form.port.trim()) return failStep2("请填写端口号");
      if (!isValidPort(form.port)) return failStep2("端口号必须为1-65535的整数");
      if (!form.area) return failStep2("请选择所属区域");
      if (!form.registerExpire.trim()) return failStep2("请填写注册有效期");
      const registerExpire = parseInt(form.registerExpire, 10);
      if (Number.isNaN(registerExpire)) return failStep2("注册有效期必须为整数");
      if (!form.heartbeat.trim()) return failStep2("请填写心跳周期");
      const heartbeat = parseInt(form.heartbeat, 10);
      if (Number.isNaN(heartbeat)) return failStep2("心跳周期必须为整数");
      if (!form.gbCode.trim()) return failStep2("请填写国标域编码");
      if (!isValidGbCode(form.gbCode)) return failStep2("国标域编码必须为20位数字");
      // 未手填拉流地址时按协议由 IP/端口/用户名/密码自动拼装；无法拼装的协议必须手动填写
      let sourceUrl = form.sourceUrl.trim();
      if (!sourceUrl) {
        const built = computeSourceUrl(form.protocol, form.ip, form.port, form.username, form.password);
        if (!built) return failStep2("请填写拉流地址");
        sourceUrl = built;
      }
      if (!form.nvrChannel.trim()) {
        this.showToast("请填写通道号");
        return;
      }
      if (!isValidChannelNo(form.nvrChannel)) {
        this.showToast(`通道号必须为1-${MAX_CHANNEL_NO}的整数`);
        return;
      }
      if (!form.channelName.trim()) {
        this.showToast("请填写通道名称");
        return;
      }
      this.saving = true;
      try {
        await api.createCamera({
          name: form.name.trim(),
          sourceUrl,
          description: form.description || undefined,
          area: form.area || undefined,
          protocol: form.protocol,
          vendor: form.vendor === "其他厂商" ? "其他" : form.vendor,
          ip: form.ip || undefined,
          port: form.port || undefined,
          username: form.username || undefined,
          password: form.password || undefined,
          serialNumber: form.serialNumber || undefined,
          nvrChannel: form.nvrChannel || undefined,
          nvrStreamType: form.nvrStreamType || undefined,
          deviceCategory: form.deviceCategory || undefined,
          deviceType: form.deviceType || undefined,
          protocolVersion: form.protocolVersion || undefined,
          registerExpire,
          heartbeat,
          gbCode: form.gbCode || undefined,
          channelName: form.channelName || undefined,
          videoPreviewEnabled: form.capabilityVideo,
          audioEnabled: form.capabilityAudio,
          talkbackEnabled: form.capabilityTalkback,
          ptzEnabled: form.capabilityPtz,
          smartAnalysisEnabled: form.capabilitySmartAnalysis,
          alarmIoEnabled: form.capabilityAlarmIo
        });
        this.showToast("新设备已保存，已加入设备管理列表");
        this.refreshCameras();
        this.setRoute("media");
      } catch (error: any) {
        this.showToast(`设备保存失败：${error?.message || error}`);
      } finally {
        this.saving = false;
      }
    }
  },
  async mounted() {
    try {
      // 「所属区域」下拉与设备管理页「所在区域」同源，来自后端区域树
      this.regionFlat = flattenRegionTree(await loadRegionTree());
    } catch {
      // 区域列表加载失败时保留下拉为空
    }
  }
});
</script>
