<template>
  <section class="content wide search-experience-page text-image-page">
    <div class="search-page-head"><div class="title-row"><div><h1 class="page-title">文搜图</h1><p class="page-subtitle">文字描述人员或车辆属性搜索图片</p></div></div></div>
    <div class="panel search-panel prototype-search-panel">
      <div class="text-image-filter-row">
        <div class="deploy-field text-image-mode-field">
          <select class="select" v-model="searchMode" aria-label="检索模式" :disabled="searching">
            <option value="exact">精确优先</option>
            <option value="balanced">均衡</option>
            <option value="fuzzy">语义优先</option>
          </select>
        </div>
        <div v-if="showSimilaritySlider" class="deploy-field text-image-similarity-field">
          <div class="track-threshold-control"><input type="range" min="0" max="100" v-model.number="confidence" aria-label="相似度阈值" /><strong>{{ confidence }}%</strong></div>
          <div class="i2i-threshold-presets">
            <button type="button" :class="{ active: confidence === 50 }" @click="confidence = 50">50%</button>
            <button type="button" :class="{ active: confidence === 70 }" @click="confidence = 70">70%</button>
            <button type="button" :class="{ active: confidence === 85 }" @click="confidence = 85">85%</button>
          </div>
        </div>
        <div class="deploy-field text-image-area-field"><area-camera-picker v-model="personFilters.area" aria-label="区域" /></div>
        <div class="deploy-field text-image-range-field"><date-time-range-picker v-model:start="personFilters.start" v-model:end="personFilters.end" /></div>
        <input class="input text-image-query-input" v-model="query" placeholder="描述你要查找的目标特征，如：戴眼镜、穿深色外套、出现在办公区附近的人员" @keyup.enter="searchImages" />
        <button class="btn primary" :disabled="searching" @click="searchImages">⌕ 搜索图片</button>
        <button class="btn" :class="{ 'ti-history-active': showHistory }" @click="toggleHistory">◷ 历史</button>
      </div>
    </div>
    <div class="text-image-body">
      <div class="text-image-results-col">
        <div class="result-toolbar"><div class="result-count">{{ searched ? '共找到' : '等待检索' }} <b>{{ searched ? totalCount : 0 }}</b> 条相似结果</div></div>
        <image-results v-if="searched" :items="paginatedResults" :show-score="searchMode !== 'exact'" :index-offset="(page - 1) * pageSize" :hide-jump="true" :hide-description="true" :show-actions="false" :emit-open="true" :media-switchable="true" :show-attributes="true" @open-result="openResultCrop"></image-results>
        <div v-if="searched" class="image-search-result-footer">
          <div class="exact-pagination">
            <span>显示 {{ pageStart }}-{{ pageEnd }} 条</span>
            <select class="select" v-model.number="pageSize" @change="handlePageSizeChange" aria-label="每页条数">
              <option v-for="size in pageSizeOptions" :key="size" :value="size">{{ size }} 条/页</option>
            </select>
            <button :disabled="page === 1 || searching" @click="goToPage(page - 1)">上一页</button>
            <template v-if="searchMode === 'fuzzy'">
              <button v-for="pageNumber in pageCount" :key="pageNumber" :class="{ active: page === pageNumber }" @click="goToPage(pageNumber)">{{ pageNumber }}</button>
            </template>
            <!-- exact/balanced 为服务端分页，接口无全局命中总数，无法渲染数字页码，仅指示当前页 -->
            <span v-else class="text-image-page-indicator">第 {{ page }} 页</span>
            <button :disabled="!hasMore || searching" @click="goToPage(page + 1)">下一页</button>
            <span>跳至</span><input class="input exact-page-jump-input" type="number" min="1" v-model="pageJump" aria-label="跳转页码" @keyup.enter="jumpToPage" /><span>页</span><button type="button" :disabled="searching" @click="jumpToPage">确定</button>
          </div>
        </div>
        <div v-else class="search-empty-state"><strong>等待图像检索</strong><span>设置筛选条件或输入目标描述后，点击「搜索图片」</span></div>
      </div>
      <aside class="text-image-insight" v-if="showHistory">
        <div class="panel ti-insight-card">
          <div class="ti-insight-head">
            <h3><span class="ti-insight-bar"></span>最近查询</h3>
            <button class="ti-hist-link" @click="placeholder('查询历史')">查看全部</button>
          </div>
          <ul class="ti-hist-list">
            <li class="ti-hist-item" v-for="item in recentQueries" :key="item.text" @click="applyRelatedSearch(item.text)">
              <span class="ti-hist-star">✦</span>
              <span class="ti-hist-text" :title="item.text">{{ item.text }}</span>
              <span class="ti-hist-count">{{ item.count }}</span>
              <span class="ti-hist-time">{{ item.time }}</span>
            </li>
          </ul>
        </div>
        <div class="panel ti-insight-card">
          <div class="ti-insight-head">
            <h3><span class="ti-insight-bar"></span>查询热词</h3>
            <button class="ti-hist-link" @click="placeholder('热词换一批')">换一批</button>
          </div>
          <div class="ti-hot-tags">
            <button v-for="(word, index) in hotWords" :key="word.text" class="ti-hot-tag" :class="{ 'ti-hot-tag-top': index < 3 }" @click="applyRelatedSearch(word.text)"><template v-if="index < 3">🔥</template>{{ word.text }}<span class="ti-hot-tag-count">{{ word.count }}</span></button>
          </div>
          <div class="ti-hot-bars">
            <div class="ti-hot-bar-row" v-for="word in hotWords.slice(0, 5)" :key="word.text" @click="applyRelatedSearch(word.text)">
              <span class="ti-hot-bar-label">{{ word.text }}</span>
              <span class="ti-hot-bar-track"><span class="ti-hot-bar-fill" :style="{ width: (word.count / maxHotCount * 100) + '%' }"></span></span>
              <span class="ti-hot-bar-count">{{ word.count }}</span>
            </div>
          </div>
        </div>
        <div class="panel ti-insight-card">
          <div class="ti-insight-head">
            <h3><span class="ti-insight-bar"></span>常用查询</h3>
            <button class="ti-hist-link" @click="placeholder('常用查询管理')">管理</button>
          </div>
          <button class="ti-hist-new" @click="placeholder('新建常用查询')">＋ 新建常用查询</button>
        </div>
      </aside>
      <aside class="text-image-insight" v-else>
        <div class="panel ti-insight-card">
          <div class="ti-insight-head">
            <h3><span class="ti-insight-bar"></span>查询理解</h3>
            <div class="ti-insight-head-actions"><span class="ti-llm-pill">LLM 解析 {{ llmDurationText }}</span><button class="btn ti-edit-btn" @click="placeholder('查询理解编辑')">编辑</button></div>
          </div>
          <!-- 检索后有真实查询理解结果（process.understanding.messages）时展示真实数据，否则展示占位卡片 -->
          <div v-if="understandingMessages.length" class="ti-attr-grid">
            <div class="ti-attr-card ti-attr-card-wide">
              <span class="ti-attr-label">{{ process?.understanding?.title || '查询理解' }}</span>
              <strong v-for="(msg, i) in understandingMessages" :key="i">{{ msg }}</strong>
            </div>
          </div>
          <div v-else class="ti-attr-grid">
            <div class="ti-attr-card"><span class="ti-attr-label">目标类型</span><strong>人体 · 行人</strong></div>
            <div class="ti-attr-card"><span class="ti-attr-label">上衣</span><strong class="ti-attr-warn">红色 · 外套</strong></div>
            <div class="ti-attr-card"><span class="ti-attr-label">背包</span><strong>双肩包（深色）</strong></div>
            <div class="ti-attr-card"><span class="ti-attr-label">行为</span><strong>步行 · 自西向东</strong></div>
            <div class="ti-attr-card"><span class="ti-attr-label">时间</span><strong class="ti-attr-link">2026-09-09 12:00–18:00</strong></div>
            <div class="ti-attr-card"><span class="ti-attr-label">地点</span><strong class="ti-attr-link">科创园东区（12 通道）</strong></div>
            <div class="ti-attr-card ti-attr-card-wide"><span class="ti-attr-label">检索策略</span><strong class="ti-attr-link">属性匹配 + 行为相似度检索 0.3 + 环境相似度检索 0.2</strong></div>
          </div>
        </div>
        <div class="panel ti-insight-card">
          <div class="ti-insight-head">
            <h3><span class="ti-insight-bar"></span>检索链路</h3>
            <span class="ti-total-time">总耗时 {{ totalDurationText }}</span>
          </div>
          <!-- 检索后绑定真实 process.steps；未检索时展示占位链路 -->
          <ol class="ti-pipeline" v-if="processSteps.length">
            <li class="ti-pipeline-step" v-for="(step, i) in processSteps" :key="step.key || i">
              <span class="ti-step-index">{{ i + 1 }}</span>
              <div class="ti-step-body">
                <div class="ti-step-row"><strong>{{ step.title }}</strong><span class="ti-step-time" v-if="step.duration_ms">{{ step.duration_ms }}ms</span></div>
                <p>{{ step.message }}</p>
              </div>
            </li>
          </ol>
          <ol class="ti-pipeline" v-else>
            <li class="ti-pipeline-step"><span class="ti-step-index">1</span><div class="ti-step-body"><div class="ti-step-row"><strong>意图理解</strong><span class="ti-step-time">38ms</span></div><p>LLM 抽取实体/属性/时空/行为 → 检索计划 · <span class="ti-step-metric">4 实体</span></p></div></li>
            <li class="ti-pipeline-step"><span class="ti-step-index">2</span><div class="ti-step-body"><div class="ti-step-row"><strong>多模态向量检索</strong><span class="ti-step-time">96ms</span></div><p>objectEmbedding 相似度检索 · <span class="ti-step-metric">召回 1,600</span></p></div></li>
            <li class="ti-pipeline-step"><span class="ti-step-index">3</span><div class="ti-step-body"><div class="ti-step-row"><strong>混合检索</strong><span class="ti-step-time">122ms</span></div><p>结构化属性 + 行为/环境文本相似度匹配 · <span class="ti-step-metric">精排 50</span></p></div></li>
            <li class="ti-pipeline-step"><span class="ti-step-index">4</span><div class="ti-step-body"><div class="ti-step-row"><strong>结果聚合</strong><span class="ti-step-time">71ms</span></div><p>时序聚合 + VLM 生成研判摘要 · <span class="ti-step-metric">聚合 5 段</span></p></div></li>
          </ol>
          <p v-if="candidateTruncated" class="text-image-candidate-tip">⚠ 语义候选已达到最大扫描窗口，结果可能不完整，可尝试提高相似度阈值或补充时间、地点条件。</p>
        </div>
        <div class="panel ti-insight-card">
          <div class="ti-insight-head">
            <h3><span class="ti-insight-bar"></span>关联搜索</h3>
            <span class="ti-related-hint">顺藤摸瓜 · 一键续查</span>
          </div>
          <div class="ti-related-list">
            <div class="ti-related-item"><span class="ti-related-icon">⌕</span><div><strong>同目标 · 放宽时间续查</strong><p>保留当前属性，时间放宽到近 7 天</p></div><button class="ti-related-btn" @click="applyRelatedSearch('红色外套深色双肩包人员 近7天')">搜索 →</button></div>
            <div class="ti-related-item"><span class="ti-related-icon">⌖</span><div><strong>同时空 · 换词续查</strong><p>昨日 12:00–18:00 东区，查其他目标</p></div><button class="ti-related-btn" @click="applyRelatedSearch('昨日12:00-18:00 东区 其他目标')">搜索 →</button></div>
            <div class="ti-related-item"><span class="ti-related-icon">✦</span><div><strong>语义联想</strong><p>模型推荐：未戴头盔、访客尾随、周界</p></div><button class="ti-related-btn" @click="applyRelatedSearch('未戴头盔 访客尾随 周界')">搜索 →</button></div>
          </div>
        </div>
        <div class="panel ti-insight-card">
          <div class="ti-insight-head">
            <h3><span class="ti-insight-bar"></span>AI 研判摘要</h3>
          </div>
          <p class="ti-summary-text">{{ aiSummary }}</p>
          <div class="ti-summary-actions"><button class="btn primary" @click="placeholder('生成研判报告')">生成研判报告</button><button class="btn" @click="copyInsightSummary">复制</button></div>
        </div>
      </aside>
    </div>
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
import { api, assetUrl } from "../api";
import type { TextSearchItem, TextSearchProcess, TextSearchProcessStep } from "../api";

type SearchMode = "exact" | "balanced" | "fuzzy";

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
      query: "",
      // 检索模式：exact 精确优先 / balanced 均衡 / fuzzy 语义优先（Retrieve API search_mode）
      searchMode: "exact" as SearchMode,
      // 模糊/均衡模式相似度阈值（%），提交时换算为 0~1 的 confidence
      confidence: 50,
      searched: false,
      page: 1,
      pageSize: 12,
      pageSizeOptions: [12, 24, 36],
      pageJump: "",
      // 结果图框选弹窗（与图搜图页同一组件）：点击结果图打开，确认后携框选区域跳转图搜图
      cropDialogOpen: false,
      cropTarget: null as any,
      cropTargetIndex: -1,
      personFilters: { area: "", start: "", end: "" },
      // Real text-search state (retrieve API wiring)
      searching: false,
      realResults: [] as any[],
      // 查询理解/检索链路展示数据（process 字段）
      process: null as TextSearchProcess | null,
      resultMessage: "",
      // 服务端分页状态：balanced 取 pagination.has_more；exact 按“返回满页”推断；fuzzy 本地分页
      serverHasMore: false,
      serverReturned: 0,
      candidateTruncated: false,
      // 右侧历史栏开关与占位数据（暂无接口，点击词条可真实检索）
      showHistory: false,
      recentQueries: [
        { text: "穿红色外套、背双肩包的人员", count: 128, time: "今天 15:08" },
        { text: "未戴头盔的配送人员，今天白天", count: 96, time: "今天 14:52" },
        { text: "红色大货车，昨天 310 国道", count: 73, time: "昨天 18:40" },
        { text: "未戴安全帽靠近配电房的人", count: 54, time: "昨天 17:22" },
        { text: "访客在 A 座大堂徘徊", count: 41, time: "昨天 11:05" }
      ],
      hotWords: [
        { text: "红色外套", count: 428 },
        { text: "双肩包", count: 386 },
        { text: "未戴头盔", count: 312 },
        { text: "电瓶车配送", count: 275 },
        { text: "大货车", count: 231 },
        { text: "安全帽", count: 198 },
        { text: "访客徘徊", count: 164 },
        { text: "北门", count: 152 },
        { text: "配电房周界", count: 121 },
        { text: "310 国道", count: 98 },
        { text: "保温箱", count: 87 },
        { text: "尾随", count: 76 }
      ],
      // AI 研判摘要占位文案（暂无接口）
      aiSummary: "目标于 12:14:07 首次出现在「东门-01」，着红色长袖外套、背深色双肩包，自西向东步行；13:02–13:07 在「中央广场-03」连续三次命中并停留约 5 分钟；14:22 经「园区环路-06」向北离开，此后各通道均无命中。"
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
    showSimilaritySlider(): boolean {
      return this.searchMode !== "exact";
    },
    // LLM pill：取检索链路第一步（意图理解）耗时，未检索时占位
    llmDurationText(): string {
      const first = this.processSteps[0];
      return first && first.duration_ms ? `${first.duration_ms}ms` : "--";
    },
    // 检索链路总耗时：各步骤 duration_ms 之和，未检索时占位
    totalDurationText(): string {
      if (!this.processSteps.length) {
        return "--";
      }
      const total = this.processSteps.reduce((sum, step) => sum + (Number(step.duration_ms) || 0), 0);
      return `${total} ms`;
    },
    maxHotCount(): number {
      return this.hotWords.length ? Math.max(...this.hotWords.map((w) => w.count)) : 1;
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
    toggleHistory() {
      this.showHistory = !this.showHistory;
    },
    // 无接口功能的统一占位提示
    placeholder(feature: string) {
      (this as any).showToast(`${feature}功能暂未开放，敬请期待`);
    },
    // 最近查询/热词/关联搜索：填入查询词并真实检索
    applyRelatedSearch(text: string) {
      this.query = text;
      this.searchImages();
    },
    async copyInsightSummary() {
      try {
        await navigator.clipboard.writeText(this.aiSummary);
        (this as any).showToast("研判摘要已复制");
      } catch {
        (this as any).showToast("复制失败，请手动选择文本复制");
      }
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
      let target = Math.max(1, page);
      if (this.searchMode === "fuzzy") {
        target = Math.min(target, this.pageCount);
      }
      if (target === this.page || this.searching) return;
      this.page = target;
      if (this.searchMode === "fuzzy") {
        // fuzzy 为本地分页，无需重新请求
        return;
      }
      this.runQuery();
    },
    jumpToPage() {
      const target = parseInt(this.pageJump, 10);
      if (Number.isNaN(target)) return;
      this.goToPage(target);
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
