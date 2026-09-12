<template>
  <section class="content wide search-experience-page text-image-page">
    <div class="search-page-head"><div class="title-row"><div><h1 class="page-title">文搜图</h1><p class="page-subtitle">文字描述人员或车辆属性搜索图片</p></div></div></div>
    <div class="panel search-panel prototype-search-panel">
      <div class="text-image-filter-row">
        <div class="deploy-field text-image-area-field"><area-camera-picker v-model="personFilters.area" aria-label="区域" /></div>
        <div class="deploy-field text-image-range-field"><date-time-range-picker v-model:start="personFilters.start" v-model:end="personFilters.end" /></div>
        <input class="input text-image-query-input" v-model="query" placeholder="描述你要查找的目标特征，如：戴眼镜、穿深色外套、出现在办公区附近的人员" />
        <button class="btn primary" :disabled="searching" @click="searchImages">⌕ 搜索图片</button>
      </div>
    </div>
    <div class="result-toolbar"><div class="result-count">{{ searched ? '共找到' : '等待检索' }} <b>{{ searched ? allResults.length : 0 }}</b> 条相似结果</div></div>
    <image-results v-if="searched" :items="paginatedResults" :index-offset="(page - 1) * pageSize" :hide-jump="true" :hide-description="true" :show-actions="false" :emit-open="true" :media-switchable="true" :show-attributes="true" @open-result="openImagePreview"></image-results>
    <div v-if="searched" class="image-search-result-footer">
      <div class="exact-pagination">
        <span>显示 {{ pageStart }}-{{ pageEnd }} 共 {{ allResults.length }} 条</span>
        <select class="select" v-model.number="pageSize" @change="handlePageSizeChange" aria-label="每页条数">
          <option v-for="size in pageSizeOptions" :key="size" :value="size">{{ size }} 条/页</option>
        </select>
        <button :disabled="page === 1" @click="goToPage(page - 1)">上一页</button>
        <button v-for="pageNumber in pageCount" :key="pageNumber" :class="{ active: page === pageNumber }" @click="goToPage(pageNumber)">{{ pageNumber }}</button>
        <button :disabled="page === pageCount" @click="goToPage(page + 1)">下一页</button>
        <span>跳至</span><input class="input exact-page-jump-input" type="number" min="1" :max="pageCount" v-model="pageJump" aria-label="跳转页码" @keyup.enter="jumpToPage" /><span>页</span>
        <button type="button" @click="jumpToPage">确定</button>
      </div>
    </div>
    <div v-else class="search-empty-state"><strong>等待图像检索</strong><span>设置筛选条件或输入目标描述后，点击「搜索图片」</span></div>
    <div v-if="previewImage" class="image-lightbox" @click.self="closeImagePreview">
      <button class="image-lightbox-close" type="button" aria-label="关闭" @click="closeImagePreview">×</button>
      <img class="image-lightbox-img" :src="previewImage" alt="结果大图" />
    </div>
    <div v-if="searching" class="search-loading-mask"><div class="search-loading-box"><span class="search-loading-spinner"></span><p>正在搜索，请稍候…</p></div></div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import ImageResults from "../components/ImageResults.vue";
import AreaCameraPicker from "../components/AreaCameraPicker.vue";
import DateTimeRangePicker from "../components/DateTimeRangePicker.vue";
import { api, assetUrl } from "../api";
import type { TextSearchItem } from "../api";

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

// "2026-07-12T08:30" -> "2026-07-12 08:30:00" (retrieve API format)
function toRetrieveApiDateTime(value: string): string | undefined {
  if (!value) {
    return undefined;
  }
  const [date, rawTime = "00:00"] = value.split("T");
  const time = rawTime.length === 5 ? `${rawTime}:00` : rawTime;
  return `${date} ${time}`;
}

// Map a retrieve API item to the item shape ImageResults / DrawerHost expect.
function mapTextSearchItem(item: TextSearchItem, index: number) {
  const payload = item.payload ?? {};
  const titleParts = [
    payload.sex,
    payload.top_color?.[0] && payload.top_type ? `${payload.top_color[0]}${payload.top_type}` : payload.top_color?.[0],
    payload.bottom_color?.[0] && payload.bottom_type ? `${payload.bottom_color[0]}${payload.bottom_type}` : payload.bottom_color?.[0]
  ].filter(Boolean);
  const extra = payload as Record<string, any>;
  return {
    title: titleParts.join("·") || `检索结果 ${index + 1}`,
    image: assetUrl(payload.image_url),
    location: payload.camera_locate || payload.camera_id || "未知摄像头",
    date: formatCreateTime(payload.create_time),
    score: null,
    desc: item.esid || item.document_id || "",
    // 卡片属性行；后端暂未返回的字段以 "—" 兜底，返回后自动生效
    age: extra.age ?? "—",
    accessory: extra.accessory ?? "—",
    topColor: (payload.top_color ?? []).join("、") || "—",
    action: extra.action ?? "—"
  };
}

export default defineComponent({
  name: "TextImagePage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  components: { ImageResults, AreaCameraPicker, DateTimeRangePicker },
  inject: {
    showToast: { from: "showToast", default: (m: string) => {} },
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} }
  },
  data() {
    return {
      query: "",
      searched: false,
      page: 1,
      pageSize: 8,
      pageSizeOptions: [8, 16, 24],
      pageJump: "",
      previewImage: "",
      personFilters: { area: "", start: "", end: "" },
      // Real text-search state (retrieve API wiring)
      searching: false,
      realResults: [] as any[]
    };
  },
  computed: {
    allResults(): any[] {
      // 只展示真实接口结果；未检索或检索失败时不回退到内置 mock 图库
      return this.realResults;
    },
    pageCount(): number {
      return Math.max(1, Math.ceil(this.allResults.length / this.pageSize));
    },
    paginatedResults(): any[] {
      const start = (this.page - 1) * this.pageSize;
      return this.allResults.slice(start, start + this.pageSize);
    },
    pageStart(): number {
      return this.allResults.length ? (this.page - 1) * this.pageSize + 1 : 0;
    },
    pageEnd(): number {
      return Math.min(this.page * this.pageSize, this.allResults.length);
    }
  },
  methods: {
    async searchImages() {
      const message = this.query.trim();
      if (!message) {
        (this as any).showToast("请输入目标描述后再搜索");
        return;
      }
      if (this.searching) return;
      this.searched = true;
      this.page = 1;
      this.searching = true;
      try {
        const filters = this.personFilters;
        const response = await api.textSearchQuery({
          message,
          startTime: toRetrieveApiDateTime(filters.start),
          endTime: toRetrieveApiDateTime(filters.end),
          location: filters.area || undefined,
          page: 1,
          pageSize: 50
        });
        const items = response.data?.items ?? [];
        this.realResults = items.map(mapTextSearchItem);
        (this as any).showToast(response.message || `检索完成，共找到 ${items.length} 条结果`);
      } catch (error) {
        this.realResults = [];
        (this as any).showToast(error instanceof Error ? error.message : "文搜图检索失败");
      } finally {
        this.searching = false;
      }
    },
    goToPage(page: number) {
      this.page = Math.min(this.pageCount, Math.max(1, page));
    },
    handlePageSizeChange() {
      this.page = 1;
      this.pageJump = "";
    },
    jumpToPage() {
      const target = parseInt(this.pageJump, 10);
      if (Number.isNaN(target)) return;
      this.goToPage(target);
      this.pageJump = "";
    },
    openImagePreview(payload: any) {
      this.previewImage = payload.item.image;
    },
    closeImagePreview() {
      this.previewImage = "";
    }
  }
});
</script>
