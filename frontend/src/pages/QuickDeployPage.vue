<template>
  <section class="content wide">
    <div class="title-row"><span class="module-icon">▣</span><div><h1 class="page-title">快速布防</h1><p class="page-subtitle">上传布控目标、选择监控点位，直接创建算法布控任务</p></div></div>
    <div class="panel deploy-panel">
      <h3 class="form-section-title"><span style="color:var(--blue)">✥</span> 布防目标设定</h3>
      <div class="quick-deploy-target-grid">
        <div class="deploy-field">
          <label><span class="required">*</span>布控目标</label>
          <div class="deploy-target-field">
            <input ref="targetInput" class="hidden-file-input" type="file" accept="image/*" @change="onTargetPicked" />
            <div v-if="targetPreview" class="deploy-target-preview">
              <img :src="targetPreview" alt="布控目标" />
              <span v-if="targetCrop" class="deploy-target-crop" :style="targetCropStyle"></span>
            </div>
            <button v-else class="file-upload-tile" type="button" @click="pickTarget"><span><b>＋ 点击上传布控图像</b><br />支持 jpg / png / jpeg</span></button>
            <button v-if="targetPreview" class="deploy-target-clear" type="button" @click="clearTarget">清除</button>
          </div>
        </div>
        <div class="deploy-field">
          <label>目标描述</label>
          <textarea class="textarea" style="height:96px;" v-model="form.desc" placeholder="请输入目标特征描述，如：身穿蓝色工服、身高约175cm、戴眼镜的中年男性..."></textarea>
        </div>
      </div>
      <div class="hr"></div>
      <h3 class="form-section-title"><span style="color:var(--blue)">⌖</span> 布防范围和策略</h3>
      <div class="deploy-grid">
        <div class="deploy-field"><label><span class="required">*</span>任务名称</label><input class="input" v-model="form.name" placeholder="请输入任务名称" /></div>
        <div class="deploy-field">
          <label><span class="required">*</span>算法编号</label>
          <select class="select" v-model="form.algorithmCode" aria-label="算法编号">
            <option value="">请选择算法编号</option>
            <option v-for="item in eventInfos" :key="item.id" :value="item.code">{{ item.code }}（{{ item.name }}）</option>
          </select>
          <span v-if="!eventInfos.length" class="hint-text">暂无事件信息，请先在「事件配置 → 事件信息配置」新增事件</span>
          <span v-else-if="eventBoundAlgorithm" class="hint-text">已绑定算法：{{ eventBoundAlgorithm.name }}（{{ eventBoundAlgorithm.code }}）</span>
          <span v-else-if="form.algorithmCode" class="hint-text">未匹配到可布控算法：任务会照常创建，但 worker 不会启动算法，请到「事件配置 → 事件信息配置」补充算法编码</span>
        </div>
        <div class="deploy-field quick-deploy-wide">
          <label><span class="required">*</span>布控区域</label>
          <div class="exact-tree-select deploy-camera-tree">
            <button class="exact-tree-trigger" :class="{ open: cameraTreeOpen }" type="button" :aria-expanded="cameraTreeOpen" aria-label="布控区域" @click="cameraTreeOpen = !cameraTreeOpen"><span>{{ cameraSummary }}</span><span>{{ cameraTreeOpen ? "收起" : "展开" }}⌄</span></button>
            <div v-if="cameraTreeOpen" class="exact-tree-dropdown">
              <div class="quick-deploy-camera-actions">
                <button class="link-blue" type="button" @click="selectAllCameras">全选</button>
                <button class="link-blue" type="button" @click="clearCameras">清空</button>
                <span class="hint-text">已选 {{ form.cameraIds.length }} 台</span>
              </div>
              <div v-for="area in cameraAreas" :key="area.name">
                <button class="exact-tree-area-row" type="button" @click="toggleArea(area.name)"><span>{{ areaExpanded[area.name] ? "⌄" : "›" }} {{ area.name }}</span><span>{{ area.cameras.length }} 台设备</span></button>
                <div v-if="areaExpanded[area.name]" class="exact-tree-children">
                  <label v-for="camera in area.cameras" :key="camera.id" class="exact-tree-device deploy-tree-camera"><input type="checkbox" :checked="form.cameraIds.includes(camera.id)" :aria-label="'选择' + camera.name" @change="toggleCamera(camera.id)" /><span class="camera-name">{{ camera.name }}</span><span>{{ cameraStatusText(camera) }}</span></label>
                </div>
              </div>
              <div v-if="!cameraAreas.length" class="exact-tree-empty">{{ loading ? "监控点加载中..." : "暂无监控点数据，请先在设备管理中接入" }}</div>
            </div>
          </div>
        </div>
        <div class="deploy-field"><label>识别频次</label><input class="input" type="number" min="1" v-model.number="form.recognitionPerMinute" placeholder="每分钟识别次数" /></div>
        <div class="deploy-field">
          <label>创建后启用</label>
          <div class="effective-row">
            <button class="event-config-switch" :class="{ active: form.enabled }" type="button" :aria-label="form.enabled ? '已启用' : '已停用'" @click="form.enabled = !form.enabled"></button>
            <span class="hint-text">{{ form.enabled ? "创建后立即布控" : "创建后保持停止" }}</span>
          </div>
        </div>
      </div>
      <div class="submit-line"><button class="btn" :disabled="saving" @click="cancel">取消</button><button class="btn primary" :disabled="saving" @click="submit">{{ saving ? "提交中…" : "✓ 提交布防" }}</button></div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api } from "../api";
import type { Algorithm, Camera, DeploymentTaskCreate, EventInfo } from "../types";
import { deviceStatusLabel } from "../utils/device-status";
import { resolveEventAlgorithm } from "../utils/algorithm-binding";

type CameraArea = { name: string; cameras: Camera[] };

// 快速布防：与「布控任务 → 新建布控任务」写同一张表（POST /api/deployment-tasks），字段口径与弹窗一致。
// 算法编号取「事件信息配置」的事件编码，再按事件信息的「算法编码」反查算法；算法编码为空时
// 任务仍会创建，但 algorithmId 为空、worker 不会启动算法（与新建布控任务弹窗行为一致）。
export default defineComponent({
  name: "QuickDeployPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} },
    showToast: { from: "showToast", default: (message: string) => {} },
  },
  data() {
    return {
      loading: false,
      saving: false,
      algorithms: [] as Algorithm[],
      eventInfos: [] as EventInfo[],
      cameras: [] as Camera[],
      cameraTreeOpen: false,
      areaExpanded: {} as Record<string, boolean>,
      targetFile: null as File | null,
      targetLocalPreview: "",
      targetPhotoUrl: "",
      targetCleared: false,
      form: {
        name: "",
        desc: "",
        algorithmCode: "",
        cameraIds: [] as string[],
        recognitionPerMinute: 60,
        enabled: true
      }
    };
  },
  computed: {
    cameraAreas(): CameraArea[] {
      const groups: Record<string, Camera[]> = {};
      this.cameras.forEach(camera => {
        const area = String(camera.area || "").trim() || "未分配";
        if (!groups[area]) groups[area] = [];
        groups[area].push(camera);
      });
      return Object.keys(groups).map(name => ({ name, cameras: groups[name] }));
    },
    // 从文搜/事件列表「去布防」带入的目标图（state.prefill）以及框选区域（state.imageCrop）
    prefillImage(): string {
      return String((this.state && this.state.prefill) || "");
    },
    targetPreview(): string {
      if (this.targetLocalPreview) return this.targetLocalPreview;
      if (this.targetCleared) return "";
      return this.targetPhotoUrl;
    },
    targetCrop(): any {
      return (this.state && this.state.imageCrop) || null;
    },
    targetCropStyle(): Record<string, string> {
      const crop = this.targetCrop || { x: 0, y: 0, width: 0, height: 0 };
      return { left: `${crop.x}%`, top: `${crop.y}%`, width: `${crop.width}%`, height: `${crop.height}%` };
    },
    selectedCameras(): Camera[] {
      return this.cameras.filter(camera => this.form.cameraIds.includes(camera.id));
    },
    // 与「新建布控任务」弹窗同口径：事件编码 → 事件信息的算法编码 → 算法列表里的可布控算法
    // （事件未绑定算法编码时回落到同编码算法，见 utils/algorithm-binding）
    selectedEventInfo(): EventInfo | undefined {
      return this.eventInfos.find(item => item.code === this.form.algorithmCode);
    },
    eventBoundAlgorithm(): Algorithm | undefined {
      return resolveEventAlgorithm(this.algorithms, this.eventInfos, this.form.algorithmCode).algorithm;
    },
    selectedAreas(): string[] {
      const names = this.selectedCameras.map(camera => String(camera.area || "").trim() || "未分配");
      return Array.from(new Set(names));
    },
    cameraSummary(): string {
      const count = this.form.cameraIds.length;
      if (!count) return "请选择布控区域（可多选摄像机）";
      const names = this.selectedCameras.map(camera => camera.name);
      return names.length <= 3 ? `已选 ${count} 台：${names.join("、")}` : `已选 ${count} 台摄像机`;
    }
  },
  watch: {
    prefillImage(value: string) {
      if (!value || this.targetFile) return;
      this.targetCleared = false;
      this.targetPhotoUrl = value;
    }
  },
  mounted() {
    if (this.prefillImage) this.targetPhotoUrl = this.prefillImage;
    this.loadBaseData();
  },
  beforeUnmount() {
    if (this.targetLocalPreview) URL.revokeObjectURL(this.targetLocalPreview);
  },
  methods: {
    notify(message: string) { this.showToast(message); },
    async loadBaseData() {
      if (this.loading) return;
      this.loading = true;
      try {
        const [algorithms, eventInfos, cameras] = await Promise.all([api.algorithms(), api.eventInfos(), api.cameras()]);
        this.algorithms = algorithms || [];
        this.eventInfos = eventInfos || [];
        this.cameras = cameras || [];
        const first = this.cameraAreas[0];
        if (first) this.areaExpanded = { [first.name]: true };
      } catch (error) {
        this.notify(error instanceof Error ? error.message : "布防基础数据加载失败");
      } finally {
        this.loading = false;
      }
    },
    cameraStatusText(camera: Camera) { return deviceStatusLabel(camera); },
    toggleArea(name: string) { this.areaExpanded = { ...this.areaExpanded, [name]: !this.areaExpanded[name] }; },
    toggleCamera(id: string) {
      this.form.cameraIds = this.form.cameraIds.includes(id)
        ? this.form.cameraIds.filter(item => item !== id)
        : [...this.form.cameraIds, id];
    },
    selectAllCameras() { this.form.cameraIds = this.cameras.map(camera => camera.id); },
    clearCameras() { this.form.cameraIds = []; },
    pickTarget() {
      const input = this.$refs.targetInput as unknown as HTMLInputElement | undefined;
      if (input) input.click();
    },
    onTargetPicked(event: Event) {
      const input = event.target as HTMLInputElement;
      const file = input.files && input.files[0];
      if (!file) return;
      if (!file.type.startsWith("image/")) {
        this.notify("请选择图片文件");
        input.value = "";
        return;
      }
      if (this.targetLocalPreview) URL.revokeObjectURL(this.targetLocalPreview);
      this.targetFile = file;
      this.targetLocalPreview = URL.createObjectURL(file);
      this.targetCleared = false;
      this.notify("布控目标已添加");
    },
    clearTarget() {
      if (this.targetLocalPreview) URL.revokeObjectURL(this.targetLocalPreview);
      this.targetLocalPreview = "";
      this.targetFile = null;
      this.targetPhotoUrl = "";
      this.targetCleared = true;
      const input = this.$refs.targetInput as unknown as HTMLInputElement | undefined;
      if (input) input.value = "";
    },
    cancel() { this.setRoute("home"); },
    async submit() {
      const name = this.form.name.trim();
      if (!name) { this.notify("请输入任务名称"); return; }
      if (!this.form.algorithmCode) { this.notify("请选择算法编号"); return; }
      if (!this.form.cameraIds.length) { this.notify("请选择布控区域（至少一台摄像机）"); return; }
      if (!this.targetPreview) { this.notify("请上传布控目标图像"); return; }
      if (this.saving) return;
      this.saving = true;
      try {
        // 布控图像：本地上传的走 /api/person-search/images 换成可访问 URL，带入的 prefill 图直接复用
        let photoUrl = this.targetPhotoUrl;
        if (this.targetFile) {
          const uploaded = await api.uploadPersonSearchImage(this.targetFile);
          photoUrl = uploaded.imageUrl;
        }
        const algorithm = this.eventBoundAlgorithm;
        const body: DeploymentTaskCreate = {
          name,
          pipeline: algorithm ? algorithm.name : "",
          algorithmId: algorithm ? algorithm.id : null,
          algorithmName: algorithm ? algorithm.name : null,
          algorithmCode: this.form.algorithmCode,
          engineType: algorithm ? algorithm.engineType : null,
          cameraIds: [...this.form.cameraIds],
          faceProfileId: null,
          faceProfilePhotoUrl: photoUrl || null,
          recognitionPerMinute: Math.max(1, Math.floor(Number(this.form.recognitionPerMinute) || 60)),
          desc: this.form.desc.trim(),
          area: this.selectedAreas.join("、"),
          areaCount: this.form.cameraIds.length,
          enabled: this.form.enabled
        };
        await api.createDeploymentTask(body);
        this.notify(`布控任务已创建：${name}`);
        this.setRoute("deployTasks");
      } catch (error) {
        this.notify(error instanceof Error ? error.message : "布控任务创建失败");
      } finally {
        this.saving = false;
      }
    }
  }
});
</script>

<style scoped>
.quick-deploy-target-grid {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}
.quick-deploy-wide { grid-column: 1 / -1; }
.quick-deploy-camera-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 2px 8px 6px;
  margin-bottom: 4px;
  border-bottom: 1px solid rgba(125, 165, 224, .18);
}
.quick-deploy-camera-actions .hint-text { margin-left: auto; }
</style>
