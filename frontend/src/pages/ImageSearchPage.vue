<template>
  <section class="content wide search-experience-page image-search-page">
    <div class="search-page-head"><div class="title-row"><div><h1 class="page-title">图搜图</h1><p class="page-subtitle">通过图片精准搜索人员或者车辆</p></div></div></div>
    <div class="panel search-panel i2i-search-panel">
      <input ref="imageSearchInput" class="hidden-file-input" type="file" accept="image/*" @change="handleImageUpload" />
      <div class="i2i-form-grid">
        <button class="i2i-upload-zone" @click="triggerImageUpload" @dragover.prevent @drop.prevent="handleImageUpload">
          <img v-if="imagePreview" :src="imagePreview" alt="参考图" />
          <span v-if="imagePreview && imageCrop" class="i2i-crop-box" :style="imageCropStyle"></span>
          <span v-if="!imagePreview"><span class="upload-mark">☁</span><strong>上传图片</strong><small>点击或拖拽图片到此处</small></span>
        </button>
        <div class="i2i-filter-area">
          <div class="attribute-grid i2i-attribute-grid">
            <div class="deploy-field"><input class="input" type="datetime-local" v-model="start" aria-label="开始时间" /></div>
            <div class="deploy-field"><input class="input" type="datetime-local" v-model="end" aria-label="结束时间" /></div>
            <div class="deploy-field"><select class="select" v-model="place" aria-label="地点"><option>全部地点</option><option>南门入口</option><option>园区广场</option><option>地下车库</option><option>办公楼层</option><option>停车场</option></select></div>
            <div class="deploy-field similarity-field"><label>相似度：<b>{{ similarity }}%</b></label><input type="range" min="0" max="100" v-model.number="similarity" /></div>
            <div class="i2i-actions"><button class="btn primary" :disabled="searching" @click="searchSimilar">⌕ 搜索</button><button class="btn" @click="clearSearchImage">清除</button></div>
          </div>
        </div>
      </div>
    </div>
    <div class="result-toolbar"><div class="result-count">{{ searched ? '共找到' : '等待检索' }} <b>{{ searched ? allResults.length : 0 }}</b> 条相似结果</div><div class="result-toolbar-actions"><button class="btn" :disabled="!searched || !allResults.length" @click="toggleSelectAll">{{ isAllSelected ? '取消全选' : '全选' }}</button><button class="btn primary" :disabled="!selectedIndexes.length" @click="openTrack">⌁ 还原目标轨迹</button></div></div>
    <image-results v-if="searched" :items="paginatedResults" :show-score="true" :selectable="true" :selected-indexes="selectedIndexes" :index-offset="(page - 1) * pageSize" :hide-jump="true" :hide-description="true" :show-actions="false" @toggle-selection="toggleSelection"></image-results>
    <div v-if="searched" class="image-search-result-footer">
      <div class="exact-pagination">
        <span>显示 {{ pageStart }}-{{ pageEnd }} 共 {{ allResults.length }} 条</span>
        <select class="page-size-select" v-model.number="pageSize" @change="handlePageSizeChange" aria-label="每页条数">
          <option v-for="size in pageSizeOptions" :key="size" :value="size">{{ size }} 条/页</option>
        </select>
        <button :disabled="page === 1" @click="goToPage(page - 1)">上一页</button>
        <button v-for="pageNumber in pageCount" :key="pageNumber" :class="{ active: page === pageNumber }" @click="goToPage(pageNumber)">{{ pageNumber }}</button>
        <button :disabled="page === pageCount" @click="goToPage(page + 1)">下一页</button>
        <span class="page-jump"><input class="page-jump-input" type="number" min="1" :max="pageCount" v-model="jumpPage" placeholder="页码" aria-label="跳转页码" @keyup.enter="jumpToPage" /><button @click="jumpToPage">确定</button></span>
      </div>
    </div>
    <div v-else class="search-empty-state"><strong>等待图像检索</strong><span>上传参考图并点击「搜索」查看匹配结果</span></div>
    <image-crop-dialog :open="cropDialogOpen" :item="cropTarget" :action="cropAction" :item-index="cropTargetIndex" @close="closeResultCrop" @confirm="confirmResultCrop"></image-crop-dialog>
    <div v-if="searching" class="search-loading-mask"><div class="search-loading-box"><span class="search-loading-spinner"></span><p>正在检索相似目标，请稍候...</p></div></div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import ImageResults from "../components/ImageResults.vue";
import ImageCropDialog from "../components/ImageCropDialog.vue";
import { api, assetUrl } from "../api";
import type { PersonSearchResultResponse, SimilarPersonResult } from "../api";

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
// ImageResults renders item.date.slice(11, 19) as the time, so keep this shape.
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

// Map a backend similar_persons entry to the item shape ImageResults expects.
function mapSimilarPerson(result: SimilarPersonResult, index: number) {
  const raw = result.similarity_score;
  const score = raw === undefined || Number.isNaN(Number(raw)) ? 0 : Math.round(Number(raw) <= 1 ? Number(raw) * 100 : Number(raw));
  return {
    title: `相似人员 ${index + 1}`,
    image: assetUrl(result.image_url),
    location: result.camera_locate || result.camera_id || "未知摄像头",
    date: formatCreateTime(result.create_time),
    score,
    desc: result.es_doc_id || ""
  };
}

export default defineComponent({
  name: "ImageSearchPage",
  components: { ImageResults, ImageCropDialog },
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    showToast: { from: "showToast", default: (m: string) => {} },
    clearImage: { from: "clearImage", default: () => {} },
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} }
  },
  data() {
    return {
      query: "",
      searched: true,
      start: "2026-07-12T00:00",
      end: "2026-07-12T23:59",
      place: "全部地点",
      similarity: 50,
      imageFileName: "",
      imagePreview: this.state.prefill || "",
      imageCrop: this.state.imageCrop,
      page: 1,
      pageSize: 8,
      pageSizeOptions: [8, 16, 24, 48],
      jumpPage: "",
      selectedIndexes: [] as number[],
      cropDialogOpen: false,
      cropAction: "",
      cropTarget: null as any,
      cropTargetIndex: -1,
      // Real person-search state (batch A API wiring)
      selectedFile: null as File | null,
      searching: false,
      searchedReal: false,
      realResults: [] as any[],
      pollRunId: 0
    };
  },
  computed: {
    allResults(): any[] {
      // Once a real backend search has completed, its results replace the
      // prototype's mock gallery (this.store.results) in the result area.
      return this.searchedReal ? this.realResults : this.store.results;
    },
    pageCount() {
      return Math.max(1, Math.ceil(this.allResults.length / this.pageSize));
    },
    paginatedResults() {
      const start = (this.page - 1) * this.pageSize;
      return this.allResults.slice(start, start + this.pageSize);
    },
    pageStart() {
      return this.allResults.length ? (this.page - 1) * this.pageSize + 1 : 0;
    },
    pageEnd() {
      return Math.min(this.page * this.pageSize, this.allResults.length);
    },
    isAllSelected() {
      return this.allResults.length > 0 && this.selectedIndexes.length === this.allResults.length;
    },
    imageCropStyle() {
      const crop = this.imageCrop || { x: 0, y: 0, width: 0, height: 0 };
      return {
        left: `${crop.x}%`,
        top: `${crop.y}%`,
        width: `${crop.width}%`,
        height: `${crop.height}%`
      };
    }
  },
  methods: {
    triggerImageUpload() {
      (this.$refs.imageSearchInput as HTMLInputElement).click();
    },
    handleImageUpload(event: any) {
      const file = event.target.files && event.target.files[0];
      if (!file) return;
      if (!file.type.startsWith("image/")) {
        this.showToast("请选择图片文件");
        return;
      }
      if (this.imagePreview && this.imagePreview.startsWith("blob:")) URL.revokeObjectURL(this.imagePreview);
      this.imagePreview = URL.createObjectURL(file);
      this.imageFileName = file.name;
      this.imageCrop = null;
      this.searched = false;
      this.page = 1;
      this.selectedIndexes = [];
      this.selectedFile = file;
      this.searchedReal = false;
      this.realResults = [];
      this.pollRunId += 1;
      this.showToast("参考图已载入，请设置筛选条件后搜索");
    },
    async searchSimilar() {
      if (!this.imagePreview) {
        this.showToast("请先上传参考图片");
        return;
      }
      if (this.searching) return;
      this.searched = true;
      this.page = 1;
      this.selectedIndexes = [];
      const runId = ++this.pollRunId;
      this.searching = true;
      try {
        // 1. Upload the query image (skip when it came from a prefill URL).
        let imageUrl = "";
        if (this.selectedFile) {
          const uploaded = await api.uploadPersonSearchImage(this.selectedFile);
          imageUrl = uploaded.imageUrl;
        } else {
          imageUrl = this.imagePreview;
        }
        if (runId !== this.pollRunId) return;
        // 2. Detect persons in the query image.
        const detectResponse = await api.detectPersons(imageUrl);
        if (runId !== this.pollRunId) return;
        const detected = detectResponse.data?.detected_persons ?? [];
        if (detectResponse.data?.status !== "success" || detected.length === 0) {
          throw new Error(detectResponse.data?.message || "未检测到人，请重新上传");
        }
        // 3. Submit the search task for the first detected person.
        const submitResponse = await api.searchPersonByBbox({
          imageUrl,
          bbox: detected[0]?.bbox,
          searchMethod: "reid",
          startTime: toPersonApiDateTime(this.start),
          endTime: toPersonApiDateTime(this.end),
          similarityThreshold: this.similarity / 100,
          topK: 20
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
        this.searchedReal = false;
        this.showToast(error instanceof Error ? error.message : "图搜人任务失败");
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
          const similarPersons = payload?.similar_persons ?? [];
          this.realResults = similarPersons.map(mapSimilarPerson);
          this.searchedReal = true;
          this.showToast(payload?.message || `找到 ${similarPersons.length} 个相似人员`);
          return;
        }
        if (taskStatus === "error") {
          throw new Error(response.data?.message || "搜索任务失败");
        }
        await delay(POLL_INTERVAL_MS);
      }
      throw new Error("搜索任务超时，请稍后重试");
    },
    clearSearchImage() {
      if (this.imagePreview && this.imagePreview.startsWith("blob:")) URL.revokeObjectURL(this.imagePreview);
      this.imagePreview = "";
      this.imageFileName = "";
      this.imageCrop = null;
      this.searched = false;
      this.page = 1;
      this.selectedIndexes = [];
      this.selectedFile = null;
      this.searchedReal = false;
      this.realResults = [];
      this.pollRunId += 1;
      this.clearImage();
      if (this.$refs.imageSearchInput) (this.$refs.imageSearchInput as HTMLInputElement).value = "";
    },
    goToPage(page: number) {
      this.page = Math.min(this.pageCount, Math.max(1, page));
    },
    handlePageSizeChange() {
      this.page = 1;
      this.jumpPage = "";
    },
    jumpToPage() {
      const target = Number(this.jumpPage);
      if (this.jumpPage === "" || !Number.isFinite(target)) return;
      this.goToPage(Math.floor(target));
      this.jumpPage = "";
    },
    toggleSelectAll() {
      if (this.isAllSelected) {
        this.selectedIndexes = [];
      } else {
        this.selectedIndexes = this.allResults.map((_, index) => index);
      }
    },
    toggleSelection(index: number) {
      if (this.selectedIndexes.includes(index)) {
        this.selectedIndexes = this.selectedIndexes.filter(item => item !== index);
      } else {
        this.selectedIndexes = [...this.selectedIndexes, index].sort((a, b) => a - b);
      }
    },
    openResultCrop(payload: any) {
      this.cropAction = payload.action;
      this.cropTarget = payload.item;
      this.cropTargetIndex = payload.index;
      this.cropDialogOpen = true;
    },
    closeResultCrop() {
      this.cropDialogOpen = false;
      this.cropAction = "";
      this.cropTarget = null;
      this.cropTargetIndex = -1;
    },
    confirmResultCrop(payload: any) {
      const { action, item, index, crop: selection } = payload;
      const crop = { ...selection, sourceName: item.title, sourceTime: item.date, sourceIndex: index };
      this.closeResultCrop();
      if (action === "imageSearch") {
        this.imagePreview = item.image;
        this.imageCrop = crop;
        this.imageFileName = "";
        this.page = 1;
        this.selectedIndexes = [];
        this.setRoute("imageSearch", { prefill: item.image, imageCrop: crop });
      } else if (action === "quickDeploy") {
        this.setRoute("newDeployTask", { prefill: item.image, imageCrop: crop });
      } else if (action === "track") {
        this.setRoute("track", { prefill: item.image, imageCrop: crop, selectedIndexes: [index], trackView: "timeline" });
      }
    },
    openTrack() {
      if (!this.selectedIndexes.length) return;
      const firstSelected = this.allResults[this.selectedIndexes[0]];
      this.setRoute("track", {
        prefill: firstSelected ? firstSelected.image : this.imagePreview,
        selectedIndexes: this.selectedIndexes,
        trackView: "timeline"
      });
    }
  },
  beforeUnmount() {
    this.pollRunId += 1;
    if (this.imagePreview && this.imagePreview.startsWith("blob:")) URL.revokeObjectURL(this.imagePreview);
  }
});
</script>
