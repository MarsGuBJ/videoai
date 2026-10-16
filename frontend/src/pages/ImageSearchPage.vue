<template>
  <section class="content wide search-experience-page image-search-page">
    <div class="search-page-head"><div class="title-row"><div><h1 class="page-title">图搜图</h1><p class="page-subtitle">通过图片精准搜索人员或者车辆</p></div></div></div>
    <div class="track-workbench">
      <div class="panel search-panel track-query-panel i2i-search-panel">
        <div class="track-section-head"><div><h3>检索条件</h3></div></div>
        <input ref="imageSearchInput" class="hidden-file-input" type="file" accept="image/*" @change="handleImageUpload" />
        <div class="track-query-grid">
          <div class="track-query-block">
            <div class="field-label">目标参考图</div>
            <div v-if="imagePreview" class="upload-card track-target-upload" role="button" tabindex="0" title="点击放大并框选裁剪，拖拽可替换图片" @click="openUploadCrop" @keydown.enter="openUploadCrop" @dragover.prevent @drop.prevent="handleImageUpload">
              <img :src="imagePreview" alt="目标参考图" />
              <span v-if="imageCrop" class="transferred-crop-box" :style="imageCropStyle"></span>
              <button class="track-target-upload-btn" type="button" title="上传/更换图片" aria-label="上传/更换图片" @click.stop="triggerImageUpload">⭱</button>
            </div>
            <button v-else class="i2i-upload-zone" title="点击或拖拽图片到此处" @click="handleUploadZoneClick" @dragover.prevent @drop.prevent="handleImageUpload">
              <span><span class="upload-mark">☁</span><strong>上传图片</strong><small>点击或拖拽图片到此处</small></span>
            </button>
            <span v-if="imageFileName" class="hint-text" :title="imageFileName">{{ imageFileName }}</span>
          </div>
          <div class="track-query-block">
            <div class="field-label">时间范围</div>
            <date-time-range-picker v-model:start="start" v-model:end="end" />
          </div>
          <div class="track-query-block">
            <div class="field-label">检索区域</div>
            <area-camera-picker v-model="place" aria-label="检索区域" />
          </div>
          <div class="track-query-block">
            <div class="field-label">搜索方法</div>
            <select class="select" v-model="searchMethod" aria-label="搜索方法">
              <option value="reid">小模型</option>
              <option value="vlm">大模型</option>
            </select>
          </div>
          <div class="track-query-block">
            <div class="field-label">人员属性</div>
            <div class="i2i-attr-grid">
              <select class="select" v-model="gender" aria-label="性别"><option>全部性别</option><option>男</option><option>女</option></select>
              <select class="select" v-model="ageGroup" aria-label="年龄段"><option>全部年龄段</option><option>儿童</option><option>青年</option><option>中年</option><option>老年</option></select>
              <select class="select" v-model="topType" aria-label="上衣类型"><option>全部上衣类型</option><option>短袖</option><option>T恤</option><option>衬衫</option><option>安全背心</option><option>夹克</option><option>羽绒服</option><option>保安制服</option><option>长袖</option><option>保洁服</option><option>连衣裙</option></select>
              <select class="select" v-model="bottomColor" aria-label="下衣颜色"><option>全部上衣颜色</option><option>黑色</option><option>白色</option><option>灰色</option><option>红色</option><option>橙色</option><option>黄色</option><option>绿色</option><option>蓝色</option><option>紫色</option><option>棕色</option></select>
            </div>
          </div>
          <div class="track-query-block">
            <div class="field-label">最大返回条数</div>
            <input class="input" type="number" min="1" max="100" v-model.number="topK" aria-label="最大返回条数（topk）" />
          </div>
          <div class="track-query-block">
            <div class="field-label">相似度阈值</div>
            <div class="track-threshold-control"><input type="range" min="0" max="100" v-model.number="similarity" /><strong>{{ similarity }}%</strong></div>
            <div class="i2i-threshold-presets">
              <button type="button" :class="{ active: similarity === 50 }" @click="similarity = 50">50%</button>
              <button type="button" :class="{ active: similarity === 75 }" @click="similarity = 75">75%</button>
              <button type="button" :class="{ active: similarity === 85 }" @click="similarity = 85">85%</button>
            </div>
            <label class="video-device-include"><input type="checkbox" v-model="autoReview" />二次研判</label>
          </div>
        </div>
        <div class="track-query-actions">
          <button class="btn primary" :disabled="searching" title="搜索图片" @click="searchSimilar">⌕ 搜索图片</button>
          <button class="btn" @click="resetFilters">重置</button>
        </div>
      </div>
      <div class="track-main-grid">
        <div class="panel track-result-panel">
          <div class="track-section-head"><div><h3>搜索结果</h3></div><div class="result-count">{{ searched ? '共找到' : '等待检索' }} <b>{{ searched ? filteredResults.length : 0 }}</b> 条相似结果</div></div>
          <div v-if="searched" class="i2i-search-stats">
            <span>检索统计：</span>
            <span>命中 <b>{{ allResults.length }}</b> 条</span>
            <span>耗时 <b>{{ searchElapsedMs }}</b> ms</span>
            <span>最高相似度 <b>{{ maxScore }}%</b></span>
            <span>阈值 <b>{{ lastThreshold }}%</b></span>
          </div>
          <div v-if="searched" class="i2i-result-filters">
            <select class="select" v-model="resultFilters.shoeType" aria-label="鞋子类型"><option value="">鞋子类型</option><option>运动鞋</option><option>休闲鞋</option><option>皮鞋</option><option>拖鞋</option><option>布鞋</option><option>凉鞋</option><option>洞洞鞋</option><option>靴子</option></select>
            <select class="select" v-model="resultFilters.hairType" aria-label="头发类型"><option value="">头发类型</option><option>短发</option><option>盘发</option><option>马尾</option><option>长发</option><option>光头</option><option>寸头</option></select>
            <select class="select" v-model="resultFilters.hairColor" aria-label="头发颜色"><option value="">头发颜色</option><option>黑色</option><option>灰白</option><option>棕色</option><option>白色</option><option>红色</option><option>黄色</option></select>
            <select class="select" v-model="resultFilters.action" aria-label="动作"><option value="">动作</option><option>站立</option><option>行走</option><option>吸烟</option><option>玩手机</option><option>坐着</option><option>打电话</option><option>做清洁</option></select>
            <select class="select" v-model="resultFilters.bottomType" aria-label="下装类型"><option value="">下装类型</option><option>长裤</option><option>短裤</option><option>牛仔裤</option><option>裙子</option><option>七分裤</option><option>工作裤</option><option>工装裤</option><option>运动裤</option></select>
            <select class="select" v-model="resultFilters.bottomColor" aria-label="下装颜色"><option value="">下装颜色</option><option>黑色</option><option>深灰色</option><option>深蓝色</option><option>米色</option><option>白色</option><option>卡其色</option></select>
            <button class="btn primary" @click="applyResultFilters">筛选</button>
            <button class="btn" :disabled="reviewing" :title="reviewing ? '二次研判中，请稍候' : '对勾选的命中记录做大模型二次研判（1~19 条）'" @click="startReview()">{{ reviewing ? '二次研判中...' : '二次研判' }}</button>
            <button class="btn" title="功能暂未开放" @click="todoFeature">步态过滤</button>
          </div>
          <div v-if="reviewSummary" class="i2i-review-summary">
            <span>研判结论：</span>
            <span>同一人 <b>{{ reviewSummary.sameCount }}</b></span>
            <span>不同/不确定 <b>{{ reviewSummary.differentCount }}</b></span>
            <span>耗时 <b>{{ reviewSummary.elapsedSeconds }}</b> s</span>
            <span class="i2i-review-conclusion" :title="reviewSummary.conclusion">{{ reviewSummary.conclusion }}</span>
          </div>
          <image-results v-if="searched" :items="paginatedResults" :show-score="true" :selectable="true" :selected-indexes="selectedResultIndexes" :index-offset="(page - 1) * pageSize" :hide-jump="true" :hide-description="true" :show-actions="false" :emit-open="true" :media-switchable="true" :show-attributes="true" @toggle-selection="toggleReviewSelection" @open-result="openResultSearch"></image-results>
          <div v-if="searched" class="image-search-result-footer">
            <div class="exact-pagination">
              <span>显示 {{ pageStart }}-{{ pageEnd }} 共 {{ filteredResults.length }} 条</span>
              <select class="page-size-select" v-model.number="pageSize" @change="handlePageSizeChange" aria-label="每页条数">
                <option v-for="size in pageSizeOptions" :key="size" :value="size">{{ size }} 条/页</option>
              </select>
              <button :disabled="page === 1" @click="goToPage(page - 1)">上一页</button>
              <button v-for="pageNumber in pageCount" :key="pageNumber" :class="{ active: page === pageNumber }" @click="goToPage(pageNumber)">{{ pageNumber }}</button>
              <button :disabled="page === pageCount" @click="goToPage(page + 1)">下一页</button>
              <span class="page-jump"><input class="page-jump-input" type="number" min="1" :max="pageCount" v-model="jumpPage" placeholder="页码" aria-label="跳转页码" @keyup.enter="jumpToPage" /><button @click="jumpToPage">确定</button></span>
            </div>
          </div>
          <div v-else class="search-empty-state"><img :src="emptyBg" alt="" class="search-empty-illustration" /><strong>暂无搜索结果</strong><strong>上传参考图并点击「搜索」查看匹配结果</strong></div>
        </div>
      </div>
    </div>
    <div v-if="searching" class="search-loading-mask"><div class="search-loading-box"><span class="search-loading-spinner"></span><p>正在搜索，请稍候…</p></div></div>
    <image-crop-dialog :open="cropDialogOpen" :item="cropTarget" :action="cropAction" :item-index="cropTargetIndex" :initial-bbox="cropAction === 'searchCrop' ? cropTarget?.position : null" @close="closeImageCrop" @confirm="confirmImageCrop"></image-crop-dialog>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import ImageResults from "../components/ImageResults.vue";
import ImageCropDialog from "../components/ImageCropDialog.vue";
import AreaCameraPicker from "../components/AreaCameraPicker.vue";
import DateTimeRangePicker from "../components/DateTimeRangePicker.vue";
import emptyBg from "../assets/empty_bg.png";
import { api, assetUrl } from "../api";
import type { PersonSearchBboxPoint, PersonSearchResultResponse, SimilarPersonResult } from "../api";
import { cropImageToFile, cropToPixelBbox } from "../utils/person-search";
import type { ImageCropSelection } from "../utils/person-search";
import { attributeText } from "../utils/attributes";

const POLL_INTERVAL_MS = 1500;
const POLL_MAX_ATTEMPTS = 60;
// 二次研判为独立异步任务（大模型推理慢，官方样例 6 人约 48s），轮询上限放宽到约 3 分钟
const REVIEW_POLL_MAX_ATTEMPTS = 120;

// 结果二次筛选的 6 个属性字段（对齐原型 resultFilters）
type ResultFilterKey = "shoeType" | "hairType" | "hairColor" | "action" | "bottomType" | "bottomColor";
const RESULT_FILTER_KEYS: ResultFilterKey[] = ["shoeType", "hairType", "hairColor", "action", "bottomType", "bottomColor"];

function emptyResultFilters(): Record<ResultFilterKey, string> {
  return { shoeType: "", hairType: "", hairColor: "", action: "", bottomType: "", bottomColor: "" };
}

// 年龄段数值映射：结果 age 为数值时按区间判定，为文本（"青年"等）时直接包含匹配
const AGE_GROUP_RANGES: Record<string, [number, number]> = {
  儿童: [0, 12],
  青年: [13, 39],
  中年: [40, 59],
  老年: [60, 200]
};

// 通用属性过滤：条件为空或以「全部」开头时不过滤；
// 结果集该字段完全无数据（上游未返回）时忽略该条件，避免误清空结果。
// stripColor：颜色字段两侧都去掉「色」再包含匹配（结果可能是「黑」也可能是「黑色」）。
function filterByField(items: any[], field: string, selected: string, stripColor = false): any[] {
  const value = (selected || "").trim();
  if (!value || value.startsWith("全部")) return items;
  const strip = (text: string) => (stripColor ? text.replace(/色/g, "") : text);
  const textOf = (item: any) => strip(attributeText(item[field]));
  if (!items.some(item => textOf(item))) return items;
  const needle = strip(value);
  return items.filter(item => textOf(item).includes(needle));
}

function filterByAgeGroup(items: any[], group: string): any[] {
  if (!group || group.startsWith("全部")) return items;
  if (!items.some(item => attributeText(item.age))) return items;
  const range = AGE_GROUP_RANGES[group];
  return items.filter(item => {
    const text = attributeText(item.age);
    if (!text) return false;
    if (text.includes(group)) return true;
    const num = Number.parseFloat(text);
    return !!range && Number.isFinite(num) && num >= range[0] && num <= range[1];
  });
}

function delay(ms: number) {
  return new Promise(resolve => {
    window.setTimeout(resolve, ms);
  });
}

// 属性下拉值 → 服务端筛选参数：「全部*」/空 = 不过滤（不传该字段）
function attributeParam(value: string): string | undefined {
  const text = (value || "").trim();
  return !text || text.startsWith("全部") ? undefined : text;
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
    // 卡片左上角 ⇄ 切换按钮播放的视频（后端 video_url 字段，无则不显示切换按钮）
    video: assetUrl(result.video_url),
    location: result.camera_locate || result.camera_id || "未知摄像头",
    date: formatCreateTime(result.create_time),
    score,
    desc: result.es_doc_id || "",
    // 二次研判候选标识：勾选记录时提交给 searchPersonReview 的 es_doc_id
    esDocId: result.es_doc_id || "",
    // 二次研判结论回填（vlm_same_person）：同一人 / 不同人；未研判为空
    reviewVerdict: "",
    reviewVerdictClass: "",
    // 目标在原图中的像素框：框选弹窗的默认框选范围
    position: result.position,
    // 属性行原样交给 ImageResults：统一去掉方括号与引号，为空时字段（含字段名）不展示
    age: result.age,
    accessory: result.accessory,
    topColor: result.top_color,
    topType: result.top_type,
    action: result.action,
    // 其余人员属性字段（ES 文档可能返回）：供人员属性条件与结果二次筛选做前端过滤
    gender: result.gender,
    bottomColor: result.bottom_color,
    shoeType: result.shoe_type,
    hairType: result.hair_type,
    hairColor: result.hair_color,
    bottomType: result.bottom_type
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
      emptyBg,
      searched: false,
      start: "",
      end: "",
      place: "",
      similarity: 75,
      // 默认不自动研判；勾选后搜索结果返回即异步发起二次研判
      autoReview: false,
      // 搜索方法：小模型(reid) / 大模型(vlm)；最大返回条数默认 10
      searchMethod: "reid",
      topK: 10,
      // 人员属性查询条件（对齐原型）：性别/年龄段/上衣类型随检索请求走服务端筛选，
      // 同时在前端再过滤一次兜底（旧版上游会忽略未知字段）；下衣颜色上游不支持，仅前端过滤
      gender: "全部性别",
      ageGroup: "全部年龄段",
      topType: "全部上衣类型",
      bottomColor: "全部上衣颜色",
      // 结果二次筛选：输入中的条件（resultFilters）点「筛选」后才应用到 appliedResultFilters
      resultFilters: emptyResultFilters(),
      appliedResultFilters: emptyResultFilters(),
      // 检索统计条：最近一次搜索的耗时与提交时的相似度阈值
      searchElapsedMs: 0,
      lastThreshold: 75,
      imageFileName: "",
      imagePreview: this.state.prefill || "",
      imageCrop: this.state.imageCrop,
      page: 1,
      pageSize: 12,
      pageSizeOptions: [12, 24, 36],
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
      cropTargetIndex: -1,
      // 二次研判：最近一次搜索的基准切片（image_url + bbox），
      // 点「二次研判」把勾选的命中记录（1~19 条）提交 searchPersonReview，结论回填到卡片角标与研判结论条
      lastSearchImageUrl: "",
      lastSearchBbox: null as PersonSearchBboxPoint[] | null,
      reviewing: false,
      reviewSummary: null as any,
      // 以 es_doc_id 记录勾选项，避免翻页或筛选后按数组下标错选其他结果
      selectedReviewIds: [] as string[]
    };
  },
  computed: {
    allResults(): any[] {
      // 只展示真实接口结果；未检索或检索失败时不回退到内置 mock 图库
      return this.realResults;
    },
    // 人员属性条件过滤（性别/年龄段/上衣类型/下衣颜色）
    attributeFilteredResults(): any[] {
      let items = this.allResults;
      items = filterByField(items, "gender", this.gender);
      items = filterByAgeGroup(items, this.ageGroup);
      items = filterByField(items, "topType", this.topType);
      items = filterByField(items, "bottomColor", this.bottomColor, true);
      return items;
    },
    // 叠加结果二次筛选（点「筛选」后生效的 appliedResultFilters）；
    // 二次研判完成后（reviewSummary 非空）只保留 vlm_same_person === true 的结果，
    // 重新搜索或重置时 reviewSummary 清空，过滤随之解除
    filteredResults(): any[] {
      let items = this.attributeFilteredResults;
      RESULT_FILTER_KEYS.forEach(key => {
        items = filterByField(items, key, this.appliedResultFilters[key]);
      });
      if (this.reviewSummary) {
        items = items.filter(item => item.reviewVerdictClass === "same");
      }
      return items;
    },
    // ImageResults 按当前筛选结果的全局索引渲染勾选状态，选择本身仍以 esDocId 保存
    selectedResultIndexes(): number[] {
      const selected = new Set(this.selectedReviewIds);
      return this.filteredResults.reduce((indexes: number[], item: any, index: number) => {
        if (selected.has(item.esDocId)) indexes.push(index);
        return indexes;
      }, []);
    },
    maxScore(): number {
      if (!this.allResults.length) return 0;
      return Math.max(...this.allResults.map(item => item.score));
    },
    pageCount() {
      return Math.max(1, Math.ceil(this.filteredResults.length / this.pageSize));
    },
    paginatedResults() {
      const start = (this.page - 1) * this.pageSize;
      return this.filteredResults.slice(start, start + this.pageSize);
    },
    pageStart() {
      return this.filteredResults.length ? (this.page - 1) * this.pageSize + 1 : 0;
    },
    pageEnd() {
      return Math.min(this.page * this.pageSize, this.filteredResults.length);
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
      this.selectedReviewIds = [];
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
    applyResultFilters() {
      this.appliedResultFilters = { ...this.resultFilters };
      this.page = 1;
      this.jumpPage = "";
      this.showToast(`已按属性筛选，命中 ${this.filteredResults.length} 条结果`);
    },
    // 二次研判 / 步态过滤：上游接口未就绪，仅保留入口
    todoFeature() {
      this.showToast("功能暂未开放，敬请期待");
    },
    toggleReviewSelection(index: number) {
      const esDocId = this.filteredResults[index]?.esDocId;
      if (!esDocId) {
        this.showToast("该结果缺少 es_doc_id，无法参与二次研判");
        return;
      }
      if (this.selectedReviewIds.includes(esDocId)) {
        this.selectedReviewIds = this.selectedReviewIds.filter(id => id !== esDocId);
        return;
      }
      if (this.selectedReviewIds.length >= 19) {
        this.showToast("一次最多勾选 19 条结果进行二次研判");
        return;
      }
      this.selectedReviewIds = [...this.selectedReviewIds, esDocId];
    },
    // 手动研判只提交勾选项；自动研判提交当前结果（接口上限 19 条），结论回填卡片角标
    async startReview(automatic = false) {
      if (this.reviewing) return;
      if (!this.searched || !this.allResults.length) {
        this.showToast("请先搜索并获得结果");
        return;
      }
      if (!automatic && !this.selectedReviewIds.length) {
        this.showToast("请先勾选需要二次研判的搜索结果");
        return;
      }
      if (!this.lastSearchImageUrl || !this.lastSearchBbox) {
        this.showToast("缺少本次搜索的基准切片，请重新搜索后再研判");
        return;
      }
      const esIds = automatic
        ? this.filteredResults.map(item => item.esDocId).filter((id): id is string => !!id).slice(0, 19)
        : [...this.selectedReviewIds];
      if (!esIds.length) {
        this.showToast("当前结果缺少 es_doc_id，无法提交研判");
        return;
      }
      const runId = this.pollRunId;
      this.reviewing = true;
      try {
        const submitResponse = await api.searchPersonReview({
          imageUrl: this.lastSearchImageUrl,
          bbox: this.lastSearchBbox,
          esIds,
          ...(automatic ? { review: true } : {})
        });
        if (runId !== this.pollRunId) return;
        const taskId = submitResponse.data?.data?.task_id ?? submitResponse.data?.task_id;
        if (!taskId) {
          throw new Error(submitResponse.data?.message || "研判任务提交失败");
        }
        await this.pollReviewResult(taskId, runId);
      } catch (error) {
        if (runId !== this.pollRunId) return;
        this.showToast(error instanceof Error ? error.message : "二次研判失败");
      } finally {
        if (runId === this.pollRunId) {
          this.reviewing = false;
        }
      }
    },
    // 轮询研判任务，完成后按 es_doc_id 把 vlm_same_person 回填到结果卡片
    async pollReviewResult(taskId: string, runId: number) {
      for (let attempt = 0; attempt < REVIEW_POLL_MAX_ATTEMPTS; attempt += 1) {
        if (runId !== this.pollRunId) return;
        const response = await api.personSearchResult(taskId);
        if (runId !== this.pollRunId) return;
        const taskStatus = response.data?.status;
        if (taskStatus === "success") {
          // 复核任务结构：data.data = { status, conclusion, same_count, different_count, elapsed_seconds, results }
          const payload = (response.data?.data ?? null) as any;
          if (payload?.status === "failed") {
            throw new Error(payload?.error || "研判服务不可用");
          }
          const results: any[] = payload?.results ?? [];
          const verdictByEsId = new Map<string, any>(results.map(entry => [entry?.es_doc_id, entry?.vlm_same_person]));
          this.realResults.forEach(item => {
            if (!verdictByEsId.has(item.esDocId)) return;
            const same = verdictByEsId.get(item.esDocId);
            item.reviewVerdict = same === true ? "同一人" : same === false ? "不同人" : "未判定";
            item.reviewVerdictClass = same === true ? "same" : same === false ? "different" : "unknown";
          });
          this.selectedReviewIds = [];
          this.reviewSummary = {
            conclusion: payload?.conclusion || "",
            sameCount: payload?.same_count ?? 0,
            differentCount: payload?.different_count ?? 0,
            elapsedSeconds: payload?.elapsed_seconds ?? 0
          };
          this.showToast(`二次研判完成：同一人 ${this.reviewSummary.sameCount} 条，不同/不确定 ${this.reviewSummary.differentCount} 条，已只显示同一人结果`);
          return;
        }
        if (taskStatus === "error") {
          throw new Error(response.data?.message || "研判任务失败");
        }
        await delay(POLL_INTERVAL_MS);
      }
      throw new Error("研判任务超时，请稍后重试");
    },
    // 重置（对齐原型）：清空全部检索条件、参考图与当前结果
    resetFilters() {
      if (this.imagePreview && this.imagePreview.startsWith("blob:")) URL.revokeObjectURL(this.imagePreview);
      this.imagePreview = "";
      this.imageFileName = "";
      this.imageCrop = null;
      this.selectedFile = null;
      this.start = "";
      this.end = "";
      this.place = "";
      this.similarity = 75;
      this.autoReview = false;
      this.searchMethod = "reid";
      this.topK = 10;
      this.gender = "全部性别";
      this.ageGroup = "全部年龄段";
      this.topType = "全部上衣类型";
      this.bottomColor = "全部上衣颜色";
      this.resultFilters = emptyResultFilters();
      this.appliedResultFilters = emptyResultFilters();
      this.lastSearchImageUrl = "";
      this.lastSearchBbox = null;
      this.reviewing = false;
      this.reviewSummary = null;
      this.searched = false;
      this.realResults = [];
      this.selectedReviewIds = [];
      this.page = 1;
      this.jumpPage = "";
      this.pollRunId += 1;
      this.showToast("检索条件已重置");
    },
    async searchSimilar() {
      if (!this.imagePreview) {
        this.showToast("请先上传参考图片");
        return;
      }
      if (this.searching) return;
      const autoReview = this.autoReview;
      this.searched = true;
      this.page = 1;
      this.selectedReviewIds = [];
      this.reviewing = false;
      const startedAt = performance.now();
      this.lastThreshold = this.similarity;
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
        // 记录本次搜索的基准切片与清空上一轮研判状态（二次研判提交必填 image_url + bbox）
        this.lastSearchImageUrl = imageUrl;
        this.lastSearchBbox = bbox;
        this.reviewSummary = null;
        // 3. Submit the search task for the selected/detected target.
        //    性别/年龄段/上衣类型走服务端属性筛选（上游字段 sex/age/top_type）；
        //    下衣颜色上游不支持，仅在前端对结果过滤。
        const submitResponse = await api.searchPersonByBbox({
          imageUrl,
          bbox,
          searchMethod: this.searchMethod,
          startTime: toPersonApiDateTime(this.start),
          endTime: toPersonApiDateTime(this.end),
          similarityThreshold: this.similarity / 100,
          topK: Math.max(1, Math.floor(Number(this.topK)) || 10),
          sex: attributeParam(this.gender),
          age: attributeParam(this.ageGroup),
          topType: attributeParam(this.topType)
        });
        if (runId !== this.pollRunId) return;
        const taskId = submitResponse.data?.task_id ?? submitResponse.data?.data?.task_id;
        if (!taskId) {
          throw new Error(submitResponse.data?.message || "搜索任务提交失败");
        }
        // 4. Poll until the task finishes.
        await this.pollPersonSearchResult(taskId, runId, autoReview);
      } catch (error) {
        if (runId !== this.pollRunId) return;
        this.realResults = [];
        this.selectedReviewIds = [];
        this.showToast(error instanceof Error ? error.message : "图搜人任务失败");
      } finally {
        if (runId === this.pollRunId) {
          this.searchElapsedMs = Math.max(1, Math.round(performance.now() - startedAt));
          this.searching = false;
        }
      }
    },
    async pollPersonSearchResult(taskId: string, runId: number, autoReview = false) {
      for (let attempt = 0; attempt < POLL_MAX_ATTEMPTS; attempt += 1) {
        if (runId !== this.pollRunId) return;
        const response = await api.personSearchResult(taskId);
        if (runId !== this.pollRunId) return;
        const taskStatus = response.data?.status;
        if (taskStatus === "success") {
          const payload = personSearchResultPayload(response);
          const similarPersons = payload?.similar_persons ?? [];
          this.realResults = similarPersons.map(mapSimilarPerson);
          // 新一轮结果：清空二次筛选条件，避免旧条件误作用于新结果集
          this.resultFilters = emptyResultFilters();
          this.appliedResultFilters = emptyResultFilters();
          this.showToast(payload?.message || `找到 ${similarPersons.length} 个相似人员`);
          // 不 await：先结束搜索 loading 并展示结果，研判任务在后台独立提交和轮询
          if (autoReview && this.realResults.length) {
            void this.startReview(true);
          }
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
