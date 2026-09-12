<template>
  <section class="content wide track-page" @click="pointDropdownOpen = false">
    <div class="title-row"><div><h1 class="page-title">轨迹还原</h1><p class="page-subtitle">设置检索条件后直接生成轨迹。</p></div></div>
    <div class="track-workbench">
      <div class="panel track-query-panel">
        <div class="track-section-head"><div><h3>检索条件</h3></div></div>
        <input ref="trackTargetInput" class="hidden-file-input" type="file" accept="image/*" @change="handleTargetUpload" />
        <div class="track-query-grid">
          <div class="track-query-block track-target-block">
            <div class="field-label">目标参考图</div>
            <div class="track-target-upload-wrap">
              <button class="upload-card track-target-upload" type="button" :title="targetPreview ? '点击放大并框选裁剪目标图片' : '点击上传目标图片'" @click="handleTargetCardClick"><img v-if="targetPreview" :src="targetPreview" alt="目标参考图" /><span v-if="targetPreview && targetCrop" class="transferred-crop-box" :style="targetCropStyle"></span><span v-if="!targetPreview" class="upload-image-hint">点击上传目标图片</span></button>
              <button v-if="targetPreview" class="track-target-upload-btn" type="button" title="上传/更换图片" aria-label="上传/更换图片" @click.stop="triggerTargetUpload">⭱</button>
            </div>
            <span v-if="targetFileName" class="hint-text">{{ targetFileName }}</span>
          </div>
          <div class="track-query-block">
            <div class="field-label">时间范围</div>
            <date-time-range-picker v-model:start="trackStart" v-model:end="trackEnd" />
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
                <div v-if="!areas.length" class="hint-text" style="padding:8px 12px;">暂无监控点数据</div>
              </div>
            </div>
          </div>
          <div class="track-query-block">
            <div class="field-label">相似度阈值</div>
            <div class="track-threshold-control"><input type="range" min="0" max="100" v-model.number="trackThreshold" /><strong>{{ trackThreshold }}%</strong></div>
          </div>
        </div>
        <div class="track-query-actions">
          <button class="btn primary" :disabled="searching" @click="runCandidateSearch">⌕ 搜索候选图片</button>
        </div>
      </div>
      <div class="track-main-grid">
        <div class="panel track-result-panel">
          <div class="track-section-head">
            <div><h3>轨迹图</h3></div>
          </div>
          <div v-if="trackGenerated" class="track-result-content">
            <div class="metric-row"><span class="metric">总时长：<b>{{ trackDuration }}</b></span><span class="metric">经过点位：<b>{{ trackPointCount }}</b></span><span class="metric">轨迹置信：<b>{{ trackConfidence }}%</b></span></div>
            <div class="timeline">
              <article class="timeline-card" v-for="item in trackItems" :key="item.title">
                <div><h4>{{ item.title }}</h4><p v-if="item.desc">{{ item.desc }}</p><div class="tags"><span class="tag blue">{{ item.location }}</span><span class="tag">相似度 {{ item.score }}%</span></div></div>
                <div class="timeline-card-controls"><span class="hint-text timeline-card-date">{{ item.date.slice(11, 19) }}</span><button class="timeline-delete-btn" @click="removeTrackItem(item)">删除</button></div>
                <button class="timeline-image-button" type="button" title="点击放大查看" @click="openImagePreview(item)"><img :src="item.image" :alt="item.title" /></button>
              </article>
            </div>
          </div>
          <div class="track-empty" v-else>点击左侧“搜索候选图片”，系统将使用搜索结果直接生成轨迹图。</div>
        </div>
      </div>
      <div v-if="searching" class="search-loading-mask" @click.stop><div class="search-loading-box"><span class="search-loading-spinner"></span><p>正在搜索候选图片，请稍候...</p></div></div>
    </div>
    <div v-if="previewImage" class="image-lightbox" @click.self="closeImagePreview">
      <button class="image-lightbox-close" type="button" aria-label="关闭" @click="closeImagePreview">×</button>
      <img class="image-lightbox-img" :src="previewImage" alt="轨迹抓拍大图" />
    </div>
    <image-crop-dialog :open="cropDialogOpen" :item="cropDialogItem" action="replaceTarget" :item-index="-1" @close="cropDialogOpen = false" @confirm="handleCropConfirm"></image-crop-dialog>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api, assetUrl } from "../api";
import type { PersonSearchBboxPoint, PersonSearchResultResponse, SimilarPersonResult } from "../api";
import ImageCropDialog from "../components/ImageCropDialog.vue";
import DateTimeRangePicker from "../components/DateTimeRangePicker.vue";
import { cropImageToFile, cropToPixelBbox } from "../utils/person-search";
import type { ImageCropSelection } from "../utils/person-search";

const POLL_INTERVAL_MS = 1500;
const POLL_MAX_ATTEMPTS = 60;

function delay(ms: number) {
  return new Promise(resolve => {
    window.setTimeout(resolve, ms);
  });
}

// "2026-07-12T08:30" -> "2026-07-12 08:30:00" (person-search API format)
function toPersonApiDateTime(value: string): string | undefined {
  if (!value) {
    return undefined;
  }
  const [date, rawTime = "00:00"] = value.split("T");
  const time = rawTime.length === 5 ? `${rawTime}:00` : rawTime;
  return `${date} ${time}`;
}

function personSearchResultPayload(response: PersonSearchResultResponse | null) {
  const payload = response?.data?.data;
  return payload?.result ?? payload ?? null;
}

function pad2(n: number) {
  return n.toString().padStart(2, "0");
}

// create_time (epoch seconds/ms or string) -> "YYYY-MM-DD HH:mm:ss"
function formatCreateTime(value?: number | string): string {
  let d: Date | null = null;
  if (value !== undefined && value !== null && value !== "") {
    const numeric = Number(value);
    if (Number.isFinite(numeric)) {
      d = new Date(numeric > 10_000_000_000 ? numeric : numeric * 1000);
    } else {
      const parsed = new Date(String(value));
      if (!Number.isNaN(parsed.getTime())) {
        d = parsed;
      }
    }
  }
  if (!d || Number.isNaN(d.getTime())) {
    return value ? String(value) : "未知时间";
  }
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
}

// Map a backend similar_persons entry to the timeline item shape.
function mapSimilarPerson(result: SimilarPersonResult, index: number) {
  const raw = result.similarity_score;
  const score = raw === undefined || Number.isNaN(Number(raw)) ? 0 : Math.round(Number(raw) <= 1 ? Number(raw) * 100 : Number(raw));
  // 特征行（原型：特征：年龄/配饰/衣服颜色/行为），后端无特征字段时留空
  const extra = result as any;
  const featureParts = [
    extra.age ? `年龄:${extra.age}` : "",
    extra.accessory ? `配饰:${extra.accessory}` : "",
    extra.topColor ? `衣服颜色:${extra.topColor}` : "",
    extra.action ? `行为:${extra.action}` : ""
  ].filter(Boolean);
  return {
    title: `相似人员 ${index + 1}`,
    image: assetUrl(result.image_url),
    location: result.camera_locate || result.camera_id || "未知摄像头",
    date: formatCreateTime(result.create_time),
    score,
    desc: featureParts.length ? `特征：${featureParts.join(" ")}` : ""
  };
}

export default defineComponent({
  name: "TrackPage",
  components: { ImageCropDialog, DateTimeRangePicker },
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    showToast: { from: "showToast", default: (m: string) => {} },
  },
  data() {
    return {
      searched: false,
      searching: false,
      trackGenerated: false,
      trackStart: "",
      trackEnd: "",
      selectedArea: null as any,
      selectedCamera: null as any,
      pointDropdownOpen: false,
      expandedAreas: {} as Record<string, boolean>,
      areas: [] as any[],
      trackThreshold: 82,
      targetPreview: this.state.prefill || "",
      targetCrop: this.state.imageCrop as any,
      targetFileName: "",
      selectedFile: null as File | null,
      cropDialogOpen: false,
      previewImage: "",
      // Raw similar_persons from the backend and the mapped timeline items.
      rawPersons: [] as SimilarPersonResult[],
      trackItems: [] as any[],
      pollRunId: 0
    };
  },
  computed: {
    cropDialogItem(): any {
      if (!this.targetPreview) return null;
      return { image: this.targetPreview, title: this.targetFileName || "目标参考图" };
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
    },
    trackDuration(): string {
      if (this.trackItems.length < 2) return "0min";
      const parse = (value: string) => new Date(value.replace(" ", "T")).getTime();
      const first = parse(this.trackItems[0].date);
      const last = parse(this.trackItems[this.trackItems.length - 1].date);
      if (Number.isNaN(first) || Number.isNaN(last) || last < first) return "-";
      const minutes = Math.round((last - first) / 60000);
      const hours = Math.floor(minutes / 60);
      return hours > 0 ? `${hours}h ${minutes % 60}min` : `${minutes}min`;
    },
    trackPointCount(): number {
      return new Set(this.trackItems.map(item => item.location)).size;
    },
    trackConfidence(): number {
      if (!this.trackItems.length) return 0;
      const total = this.trackItems.reduce((sum, item) => sum + (Number(item.score) || 0), 0);
      return Math.round(total / this.trackItems.length);
    }
  },
  mounted() {
    this.loadCameras();
    // Navigated from 图搜图 with a reference image: run the search directly.
    if (this.state.prefill) {
      this.runCandidateSearch();
    }
  },
  beforeUnmount() {
    this.pollRunId += 1;
    if (this.targetPreview && this.targetPreview.startsWith("blob:")) URL.revokeObjectURL(this.targetPreview);
  },
  methods: {
    async loadCameras() {
      try {
        const cameras = await api.cameras();
        const groups = new Map<string, any[]>();
        for (const camera of cameras || []) {
          const areaName = camera.area || "未分区";
          if (!groups.has(areaName)) groups.set(areaName, []);
          groups.get(areaName)!.push({
            name: camera.name,
            code: camera.id,
            status: camera.status || "未知"
          });
        }
        this.areas = [...groups.entries()].map(([name, cams]) => ({
          name,
          count: cams.length,
          cameras: cams
        }));
        if (this.areas.length) {
          this.expandedAreas = { [this.areas[0].name]: true };
        }
      } catch (error) {
        this.showToast("监控点列表加载失败");
      }
    },
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
      // Re-apply the camera filter on existing results without re-searching.
      if (this.rawPersons.length) {
        this.applyTrackResults();
      }
    },
    applyTrackResults() {
      let persons = this.rawPersons;
      if (this.selectedCamera) {
        const { code, name } = this.selectedCamera;
        persons = persons.filter(person =>
          person.camera_id === code || person.camera_id === name ||
          person.camera_locate === name || person.camera_locate === code
        );
      }
      this.trackItems = persons
        .map(mapSimilarPerson)
        .sort((a, b) => a.date.localeCompare(b.date));
      this.trackGenerated = this.trackItems.length > 0;
    },
    async runCandidateSearch() {
      if (!this.selectedFile && !this.targetPreview) {
        this.showToast("请先上传目标参考图");
        return;
      }
      if (this.searching) return;
      this.searched = true;
      const runId = ++this.pollRunId;
      this.searching = true;
      try {
        // 1. Upload the query image (skip when it came from a prefill URL).
        let imageUrl = "";
        if (this.selectedFile) {
          const uploaded = await api.uploadPersonSearchImage(this.selectedFile);
          imageUrl = uploaded.imageUrl;
        } else {
          imageUrl = this.targetPreview;
        }
        if (runId !== this.pollRunId) return;
        // 2. Resolve the target bbox: prefer the user-selected crop region
        //    (converted from percentage to pixel coordinates); fall back to
        //    detecting persons and taking the first detection.
        let bbox: PersonSearchBboxPoint[] | undefined;
        if (this.targetCrop) {
          bbox = (await cropToPixelBbox(imageUrl, this.targetCrop)) || undefined;
          if (runId !== this.pollRunId) return;
        }
        if (!bbox) {
          const detectResponse = await api.detectPersons(imageUrl);
          if (runId !== this.pollRunId) return;
          const detected = detectResponse.data?.detected_persons ?? [];
          if (detectResponse.data?.status !== "success" || detected.length === 0) {
            throw new Error(detectResponse.data?.message || "未检测到人，请重新上传");
          }
          bbox = detected[0]?.bbox;
        }
        // 3. Submit the search task for the selected/detected target.
        const submitResponse = await api.searchPersonByBbox({
          imageUrl,
          bbox,
          searchMethod: "reid",
          startTime: toPersonApiDateTime(this.trackStart),
          endTime: toPersonApiDateTime(this.trackEnd),
          similarityThreshold: this.trackThreshold / 100,
          topK: 50
        });
        if (runId !== this.pollRunId) return;
        const taskId = submitResponse.data?.task_id ?? submitResponse.data?.data?.task_id;
        if (!taskId) {
          throw new Error(submitResponse.data?.message || "搜索任务提交失败");
        }
        // 4. Poll until the task finishes.
        await this.pollPersonSearchResult(taskId, runId);
      } catch (error) {
        if (runId !== this.pollRunId) return;
        this.trackGenerated = false;
        this.showToast(error instanceof Error ? error.message : "轨迹搜索任务失败");
      } finally {
        if (runId === this.pollRunId) {
          this.searching = false;
        }
      }
    },
    async pollPersonSearchResult(taskId: string, runId: number) {
      for (let attempt = 0; attempt < POLL_MAX_ATTEMPTS; attempt += 1) {
        if (runId !== this.pollRunId) return;
        const response = await api.personSearchResult(taskId);
        if (runId !== this.pollRunId) return;
        const taskStatus = response.data?.status;
        if (taskStatus === "success") {
          const payload = personSearchResultPayload(response);
          this.rawPersons = payload?.similar_persons ?? [];
          this.applyTrackResults();
          this.showToast(payload?.message || `找到 ${this.trackItems.length} 个候选目标，已生成轨迹`);
          return;
        }
        if (taskStatus === "error") {
          throw new Error(response.data?.message || "搜索任务失败");
        }
        await delay(POLL_INTERVAL_MS);
      }
      throw new Error("搜索任务超时，请稍后重试");
    },
    removeTrackItem(item: any) {
      const index = this.trackItems.indexOf(item);
      if (index < 0) return;
      this.trackItems.splice(index, 1);
      this.trackGenerated = this.trackItems.length > 0;
    },
    triggerTargetUpload() {
      (this.$refs.trackTargetInput as HTMLInputElement).click();
    },
    // 已上传图片时点击图片打开放大框选弹窗，未上传时打开文件选择
    handleTargetCardClick() {
      if (this.targetPreview) {
        this.cropDialogOpen = true;
      } else {
        this.triggerTargetUpload();
      }
    },
    openImagePreview(item: any) {
      this.previewImage = item?.image || "";
    },
    closeImagePreview() {
      this.previewImage = "";
    },
    // 更换/框选目标图后重置已生成的轨迹
    resetTrackState() {
      this.searched = false;
      this.rawPersons = [];
      this.trackItems = [];
      this.trackGenerated = false;
    },
    // 框选确认：本地裁剪图片并替换目标参考图（无法裁剪时退回 bbox 检索模式）
    async handleCropConfirm(payload: any) {
      this.cropDialogOpen = false;
      const crop = payload?.crop as ImageCropSelection | undefined;
      if (!crop) return;
      if (this.selectedFile) {
        try {
          const croppedFile = await cropImageToFile(
            this.targetPreview,
            crop,
            this.targetFileName || "target.jpg",
            this.selectedFile.type
          );
          if (this.targetPreview.startsWith("blob:")) URL.revokeObjectURL(this.targetPreview);
          this.targetPreview = URL.createObjectURL(croppedFile);
          this.selectedFile = croppedFile;
          this.targetFileName = croppedFile.name;
          this.targetCrop = null;
          this.resetTrackState();
          this.showToast("已用框选区域替换目标图片");
          return;
        } catch {
          // 裁剪失败（如图片损坏）时退回 bbox 检索模式
        }
      }
      this.targetCrop = crop;
      this.resetTrackState();
      this.showToast("已记录框选区域，搜索将按该区域检索");
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
      this.selectedFile = file;
      this.resetTrackState();
      this.showToast("目标图片已载入");
    }
  }
});
</script>
