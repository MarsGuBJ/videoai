<template>
  <section class="content wide search-experience-page text-image-page">
    <div class="search-page-head"><div class="title-row"><div><h1 class="page-title">文搜图</h1><p class="page-subtitle">文字描述人员或车辆属性搜索图片</p></div></div></div>
    <div class="panel search-panel prototype-search-panel">
      <div class="exact-mode-tabs text-image-mode-switch" role="tablist">
        <button v-for="opt in searchModeOptions" :key="opt.value" class="exact-mode-tab" :class="{ active: searchMode === opt.value }" role="tab" :aria-selected="searchMode === opt.value" :title="opt.tip" @click="setSearchMode(opt.value)">{{ opt.label }}</button>
      </div>
      <div class="text-image-filter-row">
        <div class="deploy-field text-image-area-field"><area-camera-picker v-model="personFilters.area" aria-label="区域" /></div>
        <div class="deploy-field text-image-range-field"><date-time-range-picker v-model:start="personFilters.start" v-model:end="personFilters.end" /></div>
        <input class="input text-image-query-input" v-model="query" placeholder="描述你要查找的目标特征，如：戴眼镜、穿深色外套、出现在办公区附近的人员" @keyup.enter="searchImages" />
        <button class="btn primary" :disabled="searching" @click="searchImages">⌕ 搜索图片</button>
      </div>
      <div class="text-image-option-row">
        <div v-if="searchMode !== 'exact'" class="text-image-option-field">
          <span class="text-image-option-label">相似度阈值</span>
          <div class="track-threshold-control"><input type="range" min="0" max="100" v-model.number="confidence" aria-label="相似度阈值" /><strong>{{ confidence }}%</strong></div>
        </div>
        <div v-if="searchMode === 'exact'" class="text-image-option-field">
          <span class="text-image-option-label">时间排序</span>
          <select class="select" v-model="sortOrder" aria-label="时间排序">
            <option value="desc">时间倒序</option>
            <option value="asc">时间正序</option>
          </select>
        </div>
      </div>
    </div>

    <!-- 分析过程：检索链路 + 查询理解（对应原型「分析过程」折叠块，数据来自 process 字段） -->
    <div v-if="searched && process" class="panel text-image-process-panel">
      <button class="text-image-process-toggle" type="button" :aria-expanded="!processCollapsed" @click="processCollapsed = !processCollapsed">
        <span>分析过程</span>
        <span class="text-image-process-summary">{{ resultMessage }}</span>
        <span class="text-image-process-caret">{{ processCollapsed ? '展开 ⌄' : '收起 ⌃' }}</span>
      </button>
      <div v-show="!processCollapsed" class="text-image-process-body">
        <div v-if="understandingMessages.length" class="text-image-understanding">
          <strong>{{ process.understanding?.title || '查询理解' }}</strong>
          <ul><li v-for="(msg, i) in understandingMessages" :key="i">{{ msg }}</li></ul>
        </div>
        <div v-if="processSteps.length" class="text-image-step-list">
          <div v-for="(step, i) in processSteps" :key="step.key || i" class="text-image-step">
            <b>{{ i + 1 }}</b>
            <div class="text-image-step-info"><strong>{{ step.title }}</strong><span>{{ step.message }}</span></div>
            <em v-if="step.duration_ms">耗时 {{ step.duration_ms }} ms</em>
          </div>
        </div>
        <p v-if="candidateTruncated" class="text-image-candidate-tip">⚠ 语义候选已达到最大扫描窗口，结果可能不完整，可尝试提高相似度阈值或补充时间、地点条件。</p>
      </div>
    </div>

    <div class="result-toolbar"><div class="result-count">{{ searched ? '共找到' : '等待检索' }} <b>{{ searched ? totalCount : 0 }}</b> 条相似结果</div></div>
    <image-results v-if="searched" :items="paginatedResults" :show-score="searchMode !== 'exact'" :index-offset="(page - 1) * pageSize" :hide-jump="true" :hide-description="true" :show-actions="false" :emit-open="true" :media-switchable="true" :show-attributes="true" @open-result="openResultCrop"></image-results>
    <div v-if="searched" class="image-search-result-footer">
      <div class="exact-pagination">
        <span>显示 {{ pageStart }}-{{ pageEnd }} 条</span>
        <select class="select" v-model.number="pageSize" @change="handlePageSizeChange" aria-label="每页条数">
          <option v-for="size in pageSizeOptions" :key="size" :value="size">{{ size }} 条/页</option>
        </select>
        <button :disabled="page === 1 || searching" @click="goToPage(page - 1)">上一页</button>
        <span class="text-image-page-indicator">第 {{ page }} 页</span>
        <button :disabled="!hasMore || searching" @click="goToPage(page + 1)">下一页</button>
      </div>
    </div>
    <div v-else class="search-empty-state"><img :src="emptyBg" alt="" class="search-empty-illustration" /><strong>暂无搜索结果</strong><strong>设置筛选条件或输入目标描述后，点击「搜索图片」</strong></div>
    <!-- 点击结果图：与图搜图页一致的框选目标弹窗，默认框选范围取该图数据的 position 像素框 -->
    <image-crop-dialog :open="cropDialogOpen" :item="cropTarget" action="imageSearch" :item-index="cropTargetIndex" :initial-bbox="cropTarget?.position" confirm-label="以图搜图" @close="closeImageCrop" @confirm="confirmImageCrop"></image-crop-dialog>
    <div v-if="searching" class="search-loading-mask"><div class="search-loading-box"><span class="search-loading-spinner"></span><p>正在搜索，请稍候…</p></div></div>
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
import type { TextSearchItem, TextSearchProcess, TextSearchProcessStep } from "../api";

type SearchMode = "exact" | "fuzzy" | "balanced";

function pad2(n: number) {
  return n.toString().padStart(2, "0");
}

// create_time (epoch seconds/ms or string) -> "YYYY-MM-DD HH:mm:ss"
// ImageResults renders item.date.slice(11, 19) as the time, so keep this shape.
function formatCreateTime(value?: number | string | null): string {
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

// "2026-07-12T08:30" -> "2026-07-12 08:30:00" (retrieve API format)
function toRetrieveApiDateTime(value: string): string | undefined {
  if (!value) {
    return undefined;
  }
  const [date, rawTime = "00:00"] = value.split("T");
  const time = rawTime.length === 5 ? `${rawTime}:00` : rawTime;
  return `${date} ${time}`;
}

// 相似度 0~1 -> 百分比字符串（ImageResults 展示为 相似度 xx%）
function similarityToPercent(value?: number | null): string {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) {
    return "0";
  }
  return (Number(value) * 100).toFixed(2);
}

// Map a retrieve API item to the item shape ImageResults / DrawerHost expect.
// exact/balanced 返回完整 ES 文档（payload），fuzzy 只返回 es_id/image_url/create_time/camera_locate/similarity 精简字段。
function mapTextSearchItem(item: TextSearchItem, index: number) {
  const payload = item.payload ?? {};
  const isFlatItem = !item.payload;
  const titleParts = [
    payload.sex,
    payload.top_color?.[0] && payload.top_type ? `${payload.top_color[0]}${payload.top_type}` : payload.top_color?.[0],
    payload.bottom_color?.[0] && payload.bottom_type ? `${payload.bottom_color[0]}${payload.bottom_type}` : payload.bottom_color?.[0]
  ].filter(Boolean);
  const extra = payload as Record<string, any>;
  return {
    title: titleParts.join("·") || `检索结果 ${index + 1}`,
    image: assetUrl(isFlatItem ? item.image_url : payload.image_url),
    // 卡片左上角 ⇄ 切换按钮播放的视频（后端 video_url 字段，无则不显示切换按钮）
    video: assetUrl(payload.video_url),
    location: (isFlatItem ? item.camera_locate : payload.camera_locate || payload.camera_id) || "未知摄像头",
    date: formatCreateTime(isFlatItem ? item.create_time : payload.create_time),
    score: similarityToPercent(item.similarity),
    desc: item.esid || item.document_id || item.es_id || "",
    // 目标在原图中的像素框：框选弹窗的默认框选范围（fuzzy 精简模式可能不返回）
    position: isFlatItem ? item.position : payload.position,
    // 卡片属性行；值由 ImageResults 统一去掉方括号与引号，为空时该字段（含字段名）不展示
    age: extra.age,
    accessory: extra.accessory,
    topColor: payload.top_color,
    action: extra.action
  };
}

export default defineComponent({
  name: "TextImagePage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  components: { ImageResults, ImageCropDialog, AreaCameraPicker, DateTimeRangePicker },
  inject: {
    showToast: { from: "showToast", default: (m: string) => {} },
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} }
  },
  data() {
    return {
      emptyBg,
      query: "",
      // 检索模式：exact 精确 / balanced 均衡 / fuzzy 模糊语义（Retrieve API search_mode）
      searchMode: "exact" as SearchMode,
      searchModeOptions: [
        { value: "exact" as SearchMode, label: "精确检索", tip: "解析属性、时间、地点等结构化条件，返回完整 ES 文档" },
        { value: "balanced" as SearchMode, label: "均衡检索", tip: "语义相似度与精确条件取交集，返回完整文档与相似度" },
        { value: "fuzzy" as SearchMode, label: "模糊语义", tip: "整句描述转向量做语义相似度检索，按相似度降序返回" }
      ],
      // 模糊/均衡模式相似度阈值（%），提交时换算为 0~1 的 confidence
      confidence: 50,
      sortOrder: "desc" as "asc" | "desc",
      searched: false,
      page: 1,
      pageSize: 12,
      pageSizeOptions: [12, 24, 36],
      // 结果图框选弹窗（与图搜图页同一组件）：点击结果图打开，确认后携框选区域跳转图搜图
      cropDialogOpen: false,
      cropTarget: null as any,
      cropTargetIndex: -1,
      personFilters: { area: "", start: "", end: "" },
      // Real text-search state (retrieve API wiring)
      searching: false,
      realResults: [] as any[],
      // 分析过程展示数据（process 字段）与结果摘要
      process: null as TextSearchProcess | null,
      processCollapsed: false,
      resultMessage: "",
      // 服务端分页状态：balanced 取 pagination.has_more；exact 按“返回满页”推断；fuzzy 本地分页
      serverHasMore: false,
      serverReturned: 0,
      candidateTruncated: false
    };
  },
  computed: {
    allResults(): any[] {
      // 只展示真实接口结果；未检索或检索失败时不回退到内置 mock 图库
      return this.realResults;
    },
    processSteps(): TextSearchProcessStep[] {
      return this.process?.steps ?? [];
    },
    understandingMessages(): string[] {
      return this.process?.understanding?.messages ?? [];
    },
    // fuzzy 为本地分页，总数即返回条数；exact/balanced 为服务端分页，总数仅表示当前页条数
    totalCount(): number {
      return this.searchMode === "fuzzy" ? this.allResults.length : this.serverReturned;
    },
    hasMore(): boolean {
      if (this.searchMode === "fuzzy") {
        return this.page < this.pageCount;
      }
      return this.serverHasMore;
    },
    pageCount(): number {
      return Math.max(1, Math.ceil(this.allResults.length / this.pageSize));
    },
    paginatedResults(): any[] {
      if (this.searchMode === "fuzzy") {
        const start = (this.page - 1) * this.pageSize;
        return this.allResults.slice(start, start + this.pageSize);
      }
      // exact/balanced 已由服务端分页，当前页数据即 allResults
      return this.allResults;
    },
    pageStart(): number {
      return this.paginatedResults.length ? (this.page - 1) * this.pageSize + 1 : 0;
    },
    pageEnd(): number {
      return (this.page - 1) * this.pageSize + this.paginatedResults.length;
    }
  },
  methods: {
    setSearchMode(mode: SearchMode) {
      if (this.searching || this.searchMode === mode) return;
      this.searchMode = mode;
    },
    async searchImages() {
      const message = this.query.trim();
      if (!message) {
        (this as any).showToast("请输入目标描述后再搜索");
        return;
      }
      if (this.searching) return;
      this.page = 1;
      await this.runQuery();
    },
    async runQuery() {
      const message = this.query.trim();
      if (!message || this.searching) return;
      this.searched = true;
      this.searching = true;
      try {
        const filters = this.personFilters;
        const response = await api.textSearchQuery({
          message,
          startTime: toRetrieveApiDateTime(filters.start),
          endTime: toRetrieveApiDateTime(filters.end),
          location: filters.area || undefined,
          searchMode: this.searchMode,
          confidence: this.searchMode === "exact" ? undefined : this.confidence / 100,
          sortOrder: this.searchMode === "exact" ? this.sortOrder : undefined,
          page: this.page,
          pageSize: this.pageSize
        });
        const data = response.data ?? {};
        const items = data.items ?? [];
        this.realResults = items.map(mapTextSearchItem);
        this.process = data.process ?? null;
        this.resultMessage = response.message || `检索完成，共找到 ${items.length} 条结果`;
        this.candidateTruncated = !!data.candidate?.truncated;
        // 分页口径：balanced 以 pagination.has_more 为准；exact 无全局命中数，按返回满页推断可能有下一页
        this.serverReturned = items.length;
        this.serverHasMore = this.searchMode === "balanced" ? !!data.pagination?.has_more : items.length >= this.pageSize;
        (this as any).showToast(this.resultMessage);
      } catch (error) {
        this.realResults = [];
        this.process = null;
        this.serverHasMore = false;
        this.serverReturned = 0;
        this.resultMessage = "";
        (this as any).showToast(error instanceof Error ? error.message : "文搜图检索失败");
      } finally {
        this.searching = false;
      }
    },
    goToPage(page: number) {
      const target = Math.max(1, page);
      if (target === this.page || this.searching) return;
      this.page = target;
      if (this.searchMode === "fuzzy") {
        // fuzzy 为本地分页，无需重新请求
        return;
      }
      this.runQuery();
    },
    handlePageSizeChange() {
      this.page = 1;
      if (this.searchMode !== "fuzzy" && this.searched) {
        this.runQuery();
      }
    },
    // 点击结果图：打开框选目标弹窗（默认框选范围取条目 position 像素框）
    openResultCrop(payload: any) {
      if (!payload || !payload.item || !payload.item.image) return;
      this.cropTarget = payload.item;
      this.cropTargetIndex = payload.index ?? -1;
      this.cropDialogOpen = true;
    },
    closeImageCrop() {
      this.cropDialogOpen = false;
      this.cropTarget = null;
      this.cropTargetIndex = -1;
    },
    // 框选确认：携结果图与框选区域跳转图搜图页（参考图预填 + 裁剪框参与检索）
    confirmImageCrop(payload: any) {
      const item = this.cropTarget;
      const crop = payload?.crop;
      this.closeImageCrop();
      if (!item || !item.image || !crop) return;
      (this as any).setRoute("imageSearch", { prefill: item.image, imageCrop: crop });
    }
  }
});
</script>
