<template>
  <section class="content wide search-experience-page image-search-page">
    <div class="search-page-head"><div class="title-row"><div><h1 class="page-title">图搜图</h1><p class="page-subtitle">通过图片精准搜索人员或者车辆</p></div></div></div>
    <div class="panel search-panel i2i-search-panel">
      <input ref="imageSearchInput" class="hidden-file-input" type="file" accept="image/*" @change="handleImageUpload" />
      <div class="i2i-form-grid">
        <button class="i2i-upload-zone" :title="imagePreview ? '点击放大并框选裁剪，拖拽可替换图片' : '点击或拖拽图片到此处'" @click="handleUploadZoneClick" @dragover.prevent @drop.prevent="handleImageUpload">
          <img v-if="imagePreview" :src="imagePreview" alt="参考图" />
          <span v-if="imagePreview && imageCrop" class="i2i-crop-box" :style="imageCropStyle"></span>
          <span v-if="imagePreview" class="i2i-reupload-hint">点击放大裁剪</span>
          <span v-if="!imagePreview"><span class="upload-mark">☁</span><strong>上传图片</strong><small>点击或拖拽图片到此处</small></span>
        </button>
        <div class="deploy-field"><date-time-range-picker v-model:start="start" v-model:end="end" /></div>
        <div class="deploy-field"><area-camera-picker v-model="place" aria-label="地点" /></div>
        <div class="deploy-field similarity-field"><label>相似度：<b>{{ similarity }}%</b></label><input type="range" min="0" max="100" v-model.number="similarity" /></div>
        <button class="btn primary" :disabled="searching" @click="searchSimilar">⌕ 搜索</button>
      </div>
    </div>
    <div class="result-toolbar"><div class="result-count">{{ searched ? '共找到' : '等待检索' }} <b>{{ searched ? allResults.length : 0 }}</b> 条相似结果</div></div>
    <image-results v-if="searched" :items="paginatedResults" :show-score="true" :index-offset="(page - 1) * pageSize" :hide-jump="true" :hide-description="true" :show-actions="false" :emit-open="true" :media-switchable="true" :show-attributes="true" @open-result="openResultSearch"></image-results>
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
    <div v-if="searching" class="search-loading-mask"><div class="search-loading-box"><span class="search-loading-spinner"></span><p>正在搜索，请稍候…</p></div></div>
    <image-crop-dialog :open="cropDialogOpen" :item="cropTarget" :action="cropAction" :item-index="cropTargetIndex" @close="closeImageCrop" @confirm="confirmImageCrop"></image-crop-dialog>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import ImageResults from "../components/ImageResults.vue";
import ImageCropDialog from "../components/ImageCropDialog.vue";
import AreaCameraPicker from "../components/AreaCameraPicker.vue";
import DateTimeRangePicker from "../components/DateTimeRangePicker.vue";
import { api, assetUrl } from "../api";
import type { PersonSearchBboxPoint, PersonSearchResultResponse, SimilarPersonResult } from "../api";
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
  const topColor = Array.isArray(result.top_color) ? result.top_color.join("、") : result.top_color;
  return {
    title: `相似人员 ${index + 1}`,
    image: assetUrl(result.image_url),
    location: result.camera_locate || result.camera_id || "未知摄像头",
    date: formatCreateTime(result.create_time),
    score,
    desc: result.es_doc_id || "",
    // 原型结果卡片的属性行；后端暂未返回时为 undefined，卡片按字段级 v-if 隐藏
    age: result.age,
    accessory: result.accessory,
    topColor,
    action: result.action
  };
}

export default defineComponent({
  name: "ImageSearchPage",
  components: { ImageResults, ImageCropDialog, AreaCameraPicker, DateTimeRangePicker },
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    showToast: { from: "showToast", default: (m: string) => {} }
  },
  data() {
    return {
      searched: false,
      start: "",
      end: "",
      place: "",
      similarity: 50,
      imageFileName: "",
      imagePreview: this.state.prefill || "",
      imageCrop: this.state.imageCrop,
      page: 1,
      pageSize: 8,
      pageSizeOptions: [8, 16, 24],
      jumpPage: "",
      // Real person-search state (batch A API wiring)
      selectedFile: null as File | null,
      searching: false,
      realResults: [] as any[],
      pollRunId: 0,
      // 共享裁剪弹窗状态（对齐原型）：replaceUpload 裁剪参考图；searchCrop 框选结果图再次搜图
      cropDialogOpen: false,
      cropAction: "" as "" | "replaceUpload" | "searchCrop",
      cropTarget: null as any,
      cropTargetIndex: -1
    };
  },
  computed: {
    allResults(): any[] {
      // 只展示真实接口结果；未检索或检索失败时不回退到内置 mock 图库
      return this.realResults;
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
    // 原型交互：无图点击触发文件选择；有图点击打开「裁剪参考图」框选弹窗
    handleUploadZoneClick() {
      if (this.imagePreview) {
        this.openUploadCrop();
      } else {
        this.triggerImageUpload();
      }
    },
    handleImageUpload(event: any) {
      const file = (event.target.files && event.target.files[0]) || (event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0]);
      if (!file) return;
      if (!file.type.startsWith("image/")) {
        this.showToast("请选择图片文件");
        return;
      }
      // Allow picking the same file again after cancelling or confirming.
      if (event.target instanceof HTMLInputElement) event.target.value = "";
      this.applyReferenceFile(file);
      this.showToast("参考图已载入，请设置筛选条件后搜索");
    },
    // 点击已上传的参考图：弹窗放大并框选，确定后用框选区域替换参考图
    openUploadCrop() {
      if (!this.imagePreview) return;
      this.cropAction = "replaceUpload";
      this.cropTarget = { image: this.imagePreview, title: this.imageFileName || "上传参考图" };
      this.cropTargetIndex = -1;
      this.cropDialogOpen = true;
    },
    // 点击搜索结果图：弹窗放大并框选，点「搜图」以框选区域在当前页重新搜索
    openResultSearch(payload: any) {
      if (!payload || !payload.item || !payload.item.image) return;
      this.cropAction = "searchCrop";
      this.cropTarget = payload.item;
      this.cropTargetIndex = payload.index ?? -1;
      this.cropDialogOpen = true;
    },
    closeImageCrop() {
      this.cropDialogOpen = false;
      this.cropAction = "";
      this.cropTarget = null;
      this.cropTargetIndex = -1;
    },
    // 用裁剪得到的图片文件替换当前参考图，并清空上次搜索结果
    applyReferenceFile(file: File) {
      if (this.imagePreview && this.imagePreview.startsWith("blob:")) URL.revokeObjectURL(this.imagePreview);
      this.imagePreview = URL.createObjectURL(file);
      this.imageFileName = file.name;
      this.imageCrop = null;
      this.searched = false;
      this.page = 1;
      this.selectedFile = file;
      this.realResults = [];
      this.pollRunId += 1;
    },
    // 框选确认：按 action 分发——replaceUpload 裁剪替换参考图；searchCrop 结果图+裁剪框原地再搜
    async confirmImageCrop(payload: any) {
      const action = this.cropAction;
      const item = this.cropTarget;
      this.closeImageCrop();
      const crop = payload?.crop as ImageCropSelection | undefined | null;
      if (action === "replaceUpload") {
        const currentUrl = this.imagePreview;
        if (!currentUrl || !crop) return;
        try {
          const cropped = await cropImageToFile(currentUrl, crop, this.imageFileName || "参考图.jpg");
          this.applyReferenceFile(cropped);
          this.showToast("已按框选区域更新参考图，请重新搜索");
        } catch {
          this.showToast("图片加载失败，请重新上传");
        }
        return;
      }
      if (action === "searchCrop") {
        if (!item || !item.image || !crop) return;
        // 原型行为：参考图直接换为结果图，裁剪框作为 bbox 参与检索，原地刷新不跳转
        if (this.imagePreview && this.imagePreview.startsWith("blob:")) URL.revokeObjectURL(this.imagePreview);
        this.imagePreview = item.image;
        this.imageFileName = "";
        this.imageCrop = crop;
        this.selectedFile = null;
        this.page = 1;
        this.searchSimilar();
      }
    },
    async searchSimilar() {
      if (!this.imagePreview) {
        this.showToast("请先上传参考图片");
        return;
      }
      if (this.searching) return;
      this.searched = true;
      this.page = 1;
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
        // 2. Resolve the target bbox: prefer the user-selected crop region
        //    (converted from percentage to pixel coordinates); fall back to
        //    detecting persons and taking the first detection.
        let bbox: PersonSearchBboxPoint[] | undefined;
        if (this.imageCrop) {
          bbox = (await cropToPixelBbox(imageUrl, this.imageCrop)) || undefined;
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
        this.realResults = [];
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
    }
  },
  beforeUnmount() {
    this.pollRunId += 1;
    if (this.imagePreview && this.imagePreview.startsWith("blob:")) URL.revokeObjectURL(this.imagePreview);
  }
});
</script>
