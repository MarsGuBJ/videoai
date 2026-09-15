<template>
  <section class="content review-wide">
    <div class="review-titlebar">
      <div><h1>新增设备</h1><p>按设备类型、接入协议和通道信息完成编码设备接入</p></div>
      <div class="segmented"><button class="btn" @click="setRoute('media')">返回设备管理</button></div>
    </div>
    <div class="media-resource-tabs" style="max-width:860px;">
      <button :class="{ active: wizardStep === 1 }" @click="wizardStep = 1"><span class="step-badge">1</span> 选择设备类型</button>
      <button :class="{ active: wizardStep === 2 }" @click="wizardStep = 2"><span class="step-badge">2</span> 配置基本信息</button>
      <button :class="{ active: wizardStep === 3 }" @click="wizardStep = 3"><span class="step-badge">3</span> 配置通道信息</button>
    </div>
    <div v-if="wizardStep === 1" class="panel form-panel">
      <h3 class="form-section-title">设备类型</h3>
      <div class="wide-field-row"><label>设备类别：</label><select class="select" v-model="form.deviceCategory"><option>编码设备</option><option>解码设备</option></select></div>
      <div class="wide-field-row"><label>设备类型：</label><select class="select" v-model="form.deviceType"><option>IPC</option><option>NVR</option><option>DVR</option></select></div>
      <div class="wide-field-row"><label>厂商类型：</label><select class="select" v-model="form.vendor"><option>海康威视</option><option>大华</option><option>宇视</option><option>华为</option><option>其他厂商</option></select></div>
      <div class="button-row"><button class="btn primary" @click="wizardStep = 2">下一步</button><button class="btn" @click="setRoute('media')">取消</button></div>
    </div>
    <div v-else-if="wizardStep === 2" class="panel form-panel" style="width:min(960px,100%);">
      <div class="modal-summary-strip"><span>设备类别：{{ form.deviceCategory }}</span><span>设备类型：{{ form.deviceType }}</span><span>厂商类型：{{ form.vendor }}</span></div>
      <h3 class="form-section-title">基本信息</h3>
      <div class="form-grid-2">
        <div class="wide-field-row"><label>接入方式：</label><select class="select" v-model="form.protocol"><option>海康 SDK</option><option>GB28181</option><option>ONVIF</option><option>Ehome / ISUP 5.0</option><option>大华 SDK</option><option>RTSP 拉流</option><option>RTMP 推流</option><option>HTTP 拉流</option><option>GA/T 1400</option></select></div>
        <div class="wide-field-row"><label>协议版本：</label><select class="select" v-model="form.protocolVersion"><option>标准协议</option><option>海康 ISUP 5.0</option><option>GB/T 28181-2022</option><option>ONVIF Profile S</option></select></div>
        <div class="wide-field-row"><label>设备名称：</label><input class="input" v-model.trim="form.name" placeholder="请输入设备名称" /></div>
        <div class="wide-field-row"><label>设备编号：</label><input class="input" v-model.trim="form.deviceCode" placeholder="请输入设备编号" /></div>
        <div class="wide-field-row"><label>设备序列号：</label><input class="input" v-model.trim="form.serialNumber" placeholder="请输入设备序列号" /></div>
        <div class="wide-field-row"><label>IP地址：</label><input class="input" v-model.trim="form.ip" placeholder="192.168.1.64" /></div>
        <div class="wide-field-row"><label>端口号：</label><input class="input" v-model.trim="form.port" placeholder="554" /></div>
        <div class="wide-field-row"><label>用户名：</label><input class="input" v-model.trim="form.username" placeholder="admin" /></div>
        <div class="wide-field-row"><label>密码：</label><input class="input" type="password" v-model="form.password" placeholder="请输入设备密码" /></div>
        <div class="wide-field-row"><label>所属区域：</label><select class="select" v-model="form.area"><option value="" disabled>请选择区域</option><option v-for="area in areaOptions" :key="area" :value="area">{{ area }}</option></select></div>
        <div class="wide-field-row"><label>设备能力：</label><span style="display:flex;gap:16px;flex-wrap:wrap;align-self:center;"><label class="video-device-include"><input type="checkbox" checked />视频</label><label class="video-device-include"><input type="checkbox" checked />音频</label><label class="video-device-include"><input type="checkbox" checked />云台</label><label class="video-device-include"><input type="checkbox" />对讲</label><label class="video-device-include"><input type="checkbox" />警告输入输出</label></span></div>
      </div>
      <div class="wide-field-row"><label>描述：</label><textarea class="textarea" style="height:80px;" v-model.trim="form.description" placeholder="请输入设备描述"></textarea></div>
      <h3 class="form-section-title">高级配置</h3>
      <div class="form-grid-2">
        <div class="wide-field-row"><label>拉流地址：</label><input class="input" v-model.trim="form.sourceUrl" placeholder="rtsp://user:pass@ip:port/stream" /></div>
        <div class="wide-field-row"><label>注册有效期：</label><input class="input" v-model.trim="form.registerExpire" placeholder="3600" /></div>
        <div class="wide-field-row"><label>心跳周期：</label><input class="input" v-model.trim="form.heartbeat" placeholder="60" /></div>
        <div class="wide-field-row"><label>国标域编码：</label><input class="input" v-model.trim="form.gbCode" placeholder="请输入 20 位国标编码" /></div>
      </div>
      <div class="button-row"><button class="btn" @click="wizardStep = 1">上一步</button><button class="btn primary" @click="wizardStep = 3">下一步</button><button class="btn" @click="setRoute('media')">取消</button></div>
    </div>
    <div v-else class="panel form-panel" style="width:min(960px,100%);">
      <h3 class="form-section-title">通道信息</h3>
      <p class="modal-hint">当前版本每台设备接入一个通道。</p>
      <div class="form-grid-2">
        <div class="wide-field-row"><label>通道号：</label><input class="input" v-model.trim="form.nvrChannel" placeholder="1" /></div>
        <div class="wide-field-row"><label>通道名称：</label><input class="input" v-model.trim="form.channelName" placeholder="默认使用设备名称" /></div>
        <div class="wide-field-row"><label>码流类型：</label><select class="select" v-model="form.nvrStreamType"><option>主码流</option><option>子码流</option></select></div>
      </div>
      <div class="button-row" style="margin-top:14px;"><button class="btn" @click="wizardStep = 2">上一步</button><button class="btn primary" :disabled="saving" @click="finishWizard">保存</button><button class="btn" @click="setRoute('media')">取消</button></div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api } from "../api";
import { buildRegionTree, canComputeSourceUrl, computeSourceUrl, isValidChannelNo, isValidGbCode, isValidIPv4, isValidPort, loadCustomRegions, MAX_CHANNEL_NO } from "../utils/regions";
import type { Camera } from "../types";

export default defineComponent({
  name: "MediaDeviceWizardPage",
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
      cameraAreas: [] as string[],
      form: {
        deviceCategory: "编码设备",
        deviceType: "IPC",
        vendor: "海康威视",
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
        nvrChannel: "1",
        channelName: "",
        nvrStreamType: "主码流"
      }
    };
  },
  computed: {
    // 与设备管理页「所在区域」筛选下拉同源：设备已占用区域 + 自定义区域
    areaOptions(): string[] {
      return buildRegionTree(this.cameraAreas, loadCustomRegions()).map((node) => node.fullPath);
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
    async finishWizard() {
      if (this.saving) return;
      const form = this.form;
      if (!form.name.trim()) {
        this.showToast("请填写设备名称");
        this.wizardStep = 2;
        return;
      }
      let sourceUrl = form.sourceUrl.trim();
      if (!sourceUrl && canComputeSourceUrl(form.protocol)) {
        // 未手填拉流地址时，IP/端口是自动拼装的必要参数
        if (!form.ip.trim()) {
          this.showToast("请填写IP地址");
          this.wizardStep = 2;
          return;
        }
        if (!form.port.trim()) {
          this.showToast("请填写端口号");
          this.wizardStep = 2;
          return;
        }
      }
      if (form.ip.trim() && !isValidIPv4(form.ip)) {
        this.showToast("IP地址格式不正确");
        this.wizardStep = 2;
        return;
      }
      if (form.port.trim() && !isValidPort(form.port)) {
        this.showToast("端口号必须为1-65535的整数");
        this.wizardStep = 2;
        return;
      }
      if (form.gbCode.trim() && !isValidGbCode(form.gbCode)) {
        this.showToast("国标域编码必须为20位数字");
        this.wizardStep = 2;
        return;
      }
      if (!isValidChannelNo(form.nvrChannel)) {
        this.showToast(`通道号必须为1-${MAX_CHANNEL_NO}的整数`);
        this.wizardStep = 3;
        return;
      }
      if (!sourceUrl) {
        const built = computeSourceUrl(form.protocol, form.ip, form.port, form.username, form.password);
        if (!built) {
          this.showToast("当前协议无法自动拼装拉流地址，请手动填写");
          this.wizardStep = 2;
          return;
        }
        sourceUrl = built;
      }
      this.saving = true;
      try {
        // 注册有效期/心跳周期解析为整数；空串视为未填写
        let registerExpire: number | undefined;
        if (form.registerExpire.trim()) {
          const parsed = parseInt(form.registerExpire, 10);
          if (Number.isNaN(parsed)) {
            this.showToast("注册有效期必须为整数");
            this.wizardStep = 2;
            return;
          }
          registerExpire = parsed;
        }
        let heartbeat: number | undefined;
        if (form.heartbeat.trim()) {
          const parsed = parseInt(form.heartbeat, 10);
          if (Number.isNaN(parsed)) {
            this.showToast("心跳周期必须为整数");
            this.wizardStep = 2;
            return;
          }
          heartbeat = parsed;
        }
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
          deviceCode: form.deviceCode || undefined,
          serialNumber: form.serialNumber || undefined,
          nvrChannel: form.nvrChannel || undefined,
          nvrStreamType: form.nvrStreamType || undefined,
          deviceCategory: form.deviceCategory || undefined,
          deviceType: form.deviceType || undefined,
          protocolVersion: form.protocolVersion || undefined,
          registerExpire,
          heartbeat,
          gbCode: form.gbCode || undefined,
          channelName: form.channelName || undefined
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
      // 「所属区域」下拉与设备管理页「所在区域」同源，需要全量设备的区域数据
      const cameras = await api.cameras();
      this.cameraAreas = (cameras || []).map((c: Camera) => c.area || "").filter((area: string) => area && area !== "未分配");
    } catch {
      // 区域列表加载失败时仅提供自定义区域
    }
  }
});
</script>
