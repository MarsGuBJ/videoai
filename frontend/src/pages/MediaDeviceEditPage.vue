<template>
  <section class="content review-wide">
    <div class="review-titlebar">
      <div><h1>编辑设备</h1><p>维护设备基础参数、接入协议与所属区域</p></div>
      <div class="segmented"><button class="btn" @click="setRoute('mediaDeviceDetail')">返回设备详情</button></div>
    </div>
    <div class="panel form-panel" style="width:min(960px,100%);">
      <h3 class="form-section-title">基础参数</h3>
      <div class="form-grid-2">
        <div class="wide-field-row"><label>设备名称：</label><input class="input" v-model.trim="form.name" placeholder="请输入设备名称" /></div>
        <div class="wide-field-row"><label>设备编号：</label><input class="input" v-model.trim="form.deviceCode" placeholder="请输入设备编号" /></div>
        <div class="wide-field-row"><label>接入协议：</label><select class="select" v-model="form.protocol"><option>海康 SDK</option><option>GB28181</option><option>ONVIF</option><option>Ehome / ISUP 5.0</option><option>大华 SDK</option><option>RTSP 拉流</option><option>RTMP 推流</option><option>HTTP 拉流</option><option>GA/T 1400</option></select></div>
        <div class="wide-field-row"><label>IP地址：</label><input class="input" v-model.trim="form.ip" placeholder="192.168.1.64" /></div>
        <div class="wide-field-row"><label>端口号：</label><input class="input" v-model.trim="form.port" placeholder="554" /></div>
        <div class="wide-field-row"><label>所属区域：</label><select class="select" v-model="form.area"><option value="">未分配</option><option v-for="area in areaOptions" :key="area" :value="area">{{ area }}</option></select></div>
        <div class="wide-field-row"><label>设备序列号：</label><input class="input" v-model.trim="form.serialNumber" placeholder="请输入设备序列号" /></div>
        <div class="wide-field-row"><label>用户名：</label><input class="input" v-model.trim="form.username" placeholder="admin" /></div>
        <div class="wide-field-row"><label>密码：</label><input class="input" type="password" v-model="form.password" placeholder="留空则不修改密码" /></div>
        <div class="wide-field-row"><label>厂商：</label><select class="select" v-model="form.vendor"><option>海康威视</option><option>大华</option><option>宇视</option><option>华为</option><option>其他</option></select></div>
      </div>
      <div class="wide-field-row"><label>拉流地址：</label><input class="input" v-model.trim="form.sourceUrl" placeholder="rtsp://user:pass@ip:port/stream" /></div>
      <div class="wide-field-row"><label>描述：</label><textarea class="textarea" style="height:80px;" v-model.trim="form.description" placeholder="请输入设备描述"></textarea></div>
      <div class="button-row"><button class="btn primary" :disabled="saving" @click="saveDevice">保存修改</button><button class="btn" @click="setRoute('mediaDeviceDetail')">取消</button></div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api } from "../api";
import type { Camera } from "../types";
import { buildRegionTree, loadCustomRegions } from "../utils/regions";

export default defineComponent({
  name: "MediaDeviceEditPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm", "selectedCamera"],
  inject: {
    setRoute: { from: "setRoute", default: (r: string, o?: any) => {} },
    showToast: { from: "showToast", default: (m: string) => {} },
    refreshCamerasImpl: { from: "refreshCameras", default: () => {} }
  },
  data() {
    return {
      saving: false,
      form: {
        name: "",
        deviceCode: "",
        serialNumber: "",
        protocol: "RTSP 拉流",
        ip: "",
        port: "",
        area: "",
        username: "",
        password: "",
        vendor: "其他",
        sourceUrl: "",
        description: ""
      }
    };
  },
  computed: {
    areaOptions(): string[] {
      const options = buildRegionTree([], loadCustomRegions()).map((node) => node.fullPath);
      if (this.form.area && !options.includes(this.form.area)) options.push(this.form.area);
      return options;
    }
  },
  methods: {
    refreshCameras() {
      (this as any).refreshCamerasImpl();
    },
    fillForm(camera: Camera) {
      this.form.name = camera.name || "";
      this.form.deviceCode = camera.deviceCode || "";
      this.form.serialNumber = camera.serialNumber || "";
      this.form.protocol = camera.protocol || "RTSP 拉流";
      this.form.ip = camera.ip || "";
      this.form.port = camera.port || "";
      this.form.area = camera.area || "";
      this.form.username = camera.username || "";
      this.form.password = "";
      this.form.vendor = camera.vendor || "其他";
      this.form.sourceUrl = camera.sourceUrl || "";
      this.form.description = camera.description || "";
    },
    async saveDevice() {
      if (this.saving) return;
      const camera = this.selectedCamera as Camera | null;
      if (!camera) return;
      if (!this.form.name.trim()) {
        (this as any).showToast("请填写设备名称");
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
        serialNumber: this.form.serialNumber || undefined
      };
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
  }
});
</script>
