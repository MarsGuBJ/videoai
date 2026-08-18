<template>
  <section class="content wide track-page" @click="pointDropdownOpen = false">
    <div class="title-row"><div><h1 class="page-title">轨迹还原</h1><p class="page-subtitle">设置检索条件后直接生成轨迹。</p></div></div>
    <div class="track-workbench">
      <div class="panel track-query-panel">
        <div class="track-section-head"><div><h3>检索条件</h3></div></div>
        <input ref="trackTargetInput" class="hidden-file-input" type="file" accept="image/*" @change="handleTargetUpload" />
        <div class="track-query-grid">
          <div class="track-query-block">
            <div class="field-label">目标参考图</div>
            <button class="upload-card track-target-upload" @click="triggerTargetUpload"><img :src="targetPreview" alt="目标参考图" /><span v-if="targetCrop" class="transferred-crop-box" :style="targetCropStyle"></span><span class="upload-image-hint">更换目标图片</span></button>
            <span v-if="targetFileName" class="hint-text">{{ targetFileName }}</span>
          </div>
          <div class="track-query-block">
            <div class="field-label">时间范围</div>
            <input class="input" type="datetime-local" v-model="trackStart" style="margin-bottom:8px;" /><input class="input" type="datetime-local" v-model="trackEnd" />
          </div>
          <div class="track-query-block" @click.stop>
            <div class="field-label">检索区域</div>
            <div class="exact-tree-select">
              <button class="exact-tree-trigger" :class="{ open: pointDropdownOpen }" type="button" @click="togglePointDropdown"><span>{{ selectedPointLabel }}</span><span>{{ pointDropdownOpen ? '收起' : '展开' }}⌄</span></button>
              <div v-if="pointDropdownOpen" class="exact-tree-dropdown">
                <div v-for="area in areas" :key="area.name">
                  <button class="exact-tree-area-row" :class="{ active: selectedArea && selectedArea.name === area.name }" type="button" @click="toggleArea(area)"><span>{{ expandedAreas[area.name] ? '⌄' : '›' }} {{ area.name }}</span><span>{{ area.count }} 台设备</span></button>
                  <div v-if="expandedAreas[area.name]" class="exact-tree-children">
                    <button v-for="camera in area.cameras" :key="camera.code" class="exact-tree-device" :class="{ active: selectedCamera && selectedCamera.code === camera.code }" type="button" @click="selectCamera(camera, area)"><span>{{ camera.name }}</span><span>{{ camera.status }}</span></button>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="track-query-block">
            <div class="field-label">相似度阈值</div>
            <div class="track-threshold-control"><input type="range" min="0" max="100" v-model.number="trackThreshold" /><strong>{{ trackThreshold }}%</strong></div>
          </div>
        </div>
        <div class="track-query-actions">
          <button class="btn primary" @click="runCandidateSearch">⌕ 搜索候选图片</button>
        </div>
      </div>
      <div class="track-main-grid">
        <div class="panel track-result-panel">
          <div class="track-section-head">
            <div><h3>轨迹图</h3></div>
          </div>
          <div v-if="trackGenerated" class="track-result-content">
            <div class="metric-row"><span class="metric">总时长：<b>40min</b></span><span class="metric">经过点位：<b>{{ selectedItems.length }}</b></span><span class="metric">轨迹置信：<b>92%</b></span></div>
            <div class="timeline">
              <article class="timeline-card" v-for="item in selectedItems" :key="item.title">
                <div><h4>{{ item.title }}</h4><p>{{ item.desc }}</p><div class="tags"><span class="tag blue">{{ item.location }}</span><span class="tag">相似度 {{ item.score }}%</span></div></div>
                <div class="timeline-card-controls"><span class="hint-text timeline-card-date">{{ item.date.slice(11, 19) }}</span><button class="timeline-delete-btn" @click="removeTrackItem(item)">删除</button></div>
                <button class="timeline-image-button" type="button" title="查看图片详情" @click="openResult(store.results.indexOf(item))"><img :src="item.image" :alt="item.title" /></button>
              </article>
            </div>
          </div>
          <div class="track-empty" v-else>点击左侧“搜索候选图片”，系统将使用搜索结果直接生成轨迹图。</div>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";

// The prototype accesses the injected openResult directly in the template;
// vue-tsc does not infer inject keys onto the template `this`, so merge it
// into ComponentCustomProperties (type-level only, runtime inject declaration
// below stays exactly as the prototype).
declare module "vue" {
  interface ComponentCustomProperties {
    openResult: (index: number) => void;
  }
}

export default defineComponent({
  name: "TrackPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    showToast: { from: "showToast", default: (m: string) => {} },
    openResult: { from: "openResult", default: (index: number) => {} },
  },
  data() {
    const initialSelectedIndexes = [...(this.state.selectedResultIndexes || [])];
    return {
      searched: initialSelectedIndexes.length > 0,
      selectedIndexes: initialSelectedIndexes,
      trackGenerated: initialSelectedIndexes.length > 0,
      trackStart: "2026-07-12T08:00",
      trackEnd: "2026-07-12T10:30",
      selectedArea: null as any,
      selectedCamera: null as any,
      pointDropdownOpen: false,
      expandedAreas: {
        "园区南门": true,
        "A座停车区": false,
        "生产通道": false,
        "仓储区域": false,
        "外围周界": false
      } as Record<string, boolean>,
      areas: [
        { name: "园区南门", count: 12, cameras: [
          { name: "南门入口枪机", code: "CAM-001", type: "枪机", status: "在线", image: this.store.img.car },
          { name: "南门广角球机", code: "CAM-002", type: "球机", status: "在线", image: this.store.img.target },
          { name: "访客通道半球", code: "CAM-009", type: "半球", status: "在线", image: this.store.img.portrait }
        ] },
        { name: "A座停车区", count: 8, cameras: [
          { name: "A1停车场东侧", code: "CAM-003", type: "枪机", status: "在线", image: this.store.img.car },
          { name: "A2停车场出口", code: "CAM-008", type: "枪机", status: "在线", image: this.store.img.target }
        ] },
        { name: "生产通道", count: 6, cameras: [
          { name: "生产通道1号门", code: "CAM-004", type: "半球", status: "在线", image: this.store.img.analyst },
          { name: "生产通道东侧", code: "CAM-010", type: "枪机", status: "在线", image: this.store.img.map }
        ] },
        { name: "仓储区域", count: 10, cameras: [
          { name: "仓储区西门", code: "CAM-005", type: "枪机", status: "连接异常", image: this.store.img.ai },
          { name: "仓储装卸口", code: "CAM-011", type: "热成像", status: "在线", image: this.store.img.mountain }
        ] },
        { name: "外围周界", count: 7, cameras: [
          { name: "外围周界北侧", code: "CAM-006", type: "热成像", status: "连接异常", image: this.store.img.mountain },
          { name: "东侧围栏通道", code: "CAM-012", type: "枪机", status: "在线", image: this.store.img.map }
        ] }
      ],
      trackThreshold: 82,
      targetPreview: this.state.prefill || this.store.img.car,
      targetCrop: this.state.imageCrop as any,
      targetFileName: ""
    };
  },
  computed: {
    selectedItems(): any[] {
      return this.selectedIndexes.map(index => this.store.results[index]).filter(Boolean);
    },
    selectedPointLabel(): string {
      if (this.selectedArea && this.selectedCamera) return `${this.selectedArea.name} / ${this.selectedCamera.name}`;
      if (this.selectedArea) return `${this.selectedArea.name} / 请选择监控点`;
      return "请选择区域 / 监控点";
    },
    targetCropStyle(): Record<string, string> {
      const crop = this.targetCrop || { x: 0, y: 0, width: 0, height: 0 };
      return {
        left: `${crop.x}%`,
        top: `${crop.y}%`,
        width: `${crop.width}%`,
        height: `${crop.height}%`
      };
    }
  },
  methods: {
    togglePointDropdown() {
      this.pointDropdownOpen = !this.pointDropdownOpen;
    },
    toggleArea(area: any) {
      if (!this.selectedArea || this.selectedArea.name !== area.name) {
        this.selectedArea = area;
        this.selectedCamera = null;
      }
      this.expandedAreas[area.name] = !this.expandedAreas[area.name];
    },
    selectCamera(camera: any, area: any) {
      this.selectedArea = area;
      this.selectedCamera = camera;
      this.pointDropdownOpen = false;
    },
    runCandidateSearch() {
      this.searched = true;
      this.selectedIndexes = this.store.results.slice(0, 6).map((_: any, index: number) => index);
      this.trackGenerated = true;
      this.showToast("已根据搜索结果生成轨迹图");
    },
    removeTrackItem(item: any) {
      const resultIndex = this.store.results.indexOf(item);
      if (resultIndex < 0) return;
      this.selectedIndexes = this.selectedIndexes.filter(index => index !== resultIndex);
      this.trackGenerated = this.selectedIndexes.length > 0;
    },
    triggerTargetUpload() {
      (this.$refs.trackTargetInput as HTMLInputElement).click();
    },
    handleTargetUpload(event: Event) {
      const input = event.target as HTMLInputElement;
      const file = input.files && input.files[0];
      if (!file) return;
      if (!file.type.startsWith("image/")) {
        this.showToast("请选择图片文件");
        return;
      }
      if (this.targetPreview && this.targetPreview.startsWith("blob:")) URL.revokeObjectURL(this.targetPreview);
      this.targetPreview = URL.createObjectURL(file);
      this.targetCrop = null;
      this.targetFileName = file.name;
      this.searched = false;
      this.selectedIndexes = [];
      this.trackGenerated = false;
      this.showToast("目标图片已载入");
    }
  }
});
</script>
