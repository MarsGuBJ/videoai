<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>事件列表</h1><p>统一管理视觉告警事件、复核状态和处置结果</p></div></div>
    <summary-cards :cards="cards"></summary-cards>
    <div class="review-board">
      <div class="page-actions"><div class="left"><button class="btn" @click="applyFilters">查询</button><button class="btn" @click="resetFilters">重置</button><input class="input" style="width:260px;" v-model="keyword" placeholder="搜索事件名称、事件ID" @keyup.enter="applyFilters" /><select class="select" style="width:140px;" v-model="reviewStatusFilter"><option value="">全部状态</option><option value="待复核">待复核</option><option value="有效">有效</option><option value="无效">无效</option></select><select class="select" style="width:150px;" v-model="eventTypeFilter"><option value="">全部类型</option><option value="face_match">人脸比对</option><option value="object_detection">目标检测</option></select><select class="select" style="width:150px;" v-model="areaFilter"><option value="">全部区域</option><option v-for="area in areas" :key="area" :value="area">{{ area }}</option></select><select class="select" style="width:170px;" v-model="taskFilter"><option value="">全部布控任务</option><option v-for="task in tasks" :key="task.id" :value="task.id">{{ task.name }}</option></select><input class="input" style="width:190px;" type="datetime-local" v-model="startTime" aria-label="开始时间" /><input class="input" style="width:190px;" type="datetime-local" v-model="endTime" aria-label="结束时间" /></div></div>
      <table class="prototype-table">
        <colgroup><col style="width:132px;" /><col style="width:220px;" /><col style="width:92px;" /><col style="width:72px;" /><col style="width:150px;" /><col style="width:130px;" /><col style="width:82px;" /><col style="width:112px;" /></colgroup>
        <thead><tr><th>事件ID</th><th class="left">事件信息</th><th>事件类型</th><th>等级</th><th class="left">事件来源</th><th>区域/点位</th><th>状态</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td class="ellipsis" :title="row.id">{{ row.id }}</td>
            <td class="left"><div class="event-name-cell"><div class="event-thumb-wrap"><img v-if="row.image" class="event-thumb" :src="row.image" :alt="row.name" style="cursor:pointer;" @click="setRoute('imageSearch', { prefill: row.image })" /><div v-else class="event-thumb"></div></div><div><h4>{{ row.name }}</h4><p>{{ row.time }}</p></div></div></td>
            <td>{{ row.type }}</td>
            <td><span class="level-pill" :class="levelClass(row.level)">{{ row.level }}</span></td>
            <td class="left ellipsis" :title="taskNameOf(row)">{{ taskNameOf(row) }}</td>
            <td>{{ areaOf(row) }}<br /><span class="hint-text">{{ row.point }}</span></td>
            <td><span class="status-pill" :class="statusClass(row.status)">{{ row.status }}</span></td>
            <td><button class="link-blue" @click="openEventDetail(row)">详情</button><button v-if="row.status !== '待复核'" class="link-blue" :disabled="handling" @click="handleEvent(row)">处理</button></td>
          </tr>
          <tr v-if="!loading && !rows.length"><td colspan="8" class="empty-cell">暂无事件</td></tr>
          <tr v-if="loading"><td colspan="8" class="empty-cell">加载中...</td></tr>
        </tbody>
      </table>
      <div class="event-config-pagination"><span style="color:#98a2b3;font-size:11px;margin-right:auto;">共 {{ total }} 条</span><button type="button" aria-label="上一页" :disabled="page <= 1" @click="gotoPage(page - 1)">‹</button><button v-for="p in pageList" :key="p" type="button" :class="{ active: page === p }" @click="gotoPage(p)">{{ p }}</button><button type="button" aria-label="下一页" :disabled="page >= totalPages" @click="gotoPage(page + 1)">›</button><select class="select" v-model.number="size" aria-label="每页条数" @change="changeSize"><option :value="10">10条/页</option><option :value="20">20条/页</option><option :value="50">50条/页</option></select></div>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import SummaryCards from "../components/SummaryCards.vue";
import { api, assetUrl } from "../api";
import type { DeploymentEvent, DeploymentTask } from "../types";

function formatEventTime(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

// 原型设计有「等级」列而事件数据无等级字段：人脸事件按相似度推导，其余显示「—」
function deriveLevel(event: DeploymentEvent): string {
  if (event.eventType !== "face_match" || event.similarity == null) return "—";
  const pct = event.similarity <= 1 ? event.similarity * 100 : event.similarity;
  if (pct >= 90) return "高";
  if (pct >= 75) return "中";
  return "低";
}

function mapEventToRow(event: DeploymentEvent) {
  const isFace = event.eventType === "face_match";
  const labels = (event.objects || []).map((obj) => obj.labelName).filter(Boolean).join("、");
  const similarity = event.similarity == null
    ? ""
    : `比对相似度 ${(event.similarity <= 1 ? event.similarity * 100 : event.similarity).toFixed(1)}%`;
  const result = isFace ? similarity || "—" : labels || "—";
  // 状态对齐原型口径：复核结论（有效/无效），未回写视为待复核
  const reviewStatus = (event.reviewStatus || "").trim();
  return {
    id: event.id,
    name: isFace ? `${event.faceProfileName || "未知人员"}人脸比对命中` : labels ? `检测到${labels}` : "目标检测事件",
    type: isFace ? "人脸比对" : "目标检测",
    level: deriveLevel(event),
    algorithmCode: event.algorithmCode || "—",
    deploymentTaskId: event.deploymentTaskId || null,
    area: event.cameraArea || "—",
    point: event.cameraName || "—",
    result,
    desc: result,
    time: formatEventTime(event.occurredAt || event.createdAt),
    image: assetUrl(event.snapshotUrl || event.faceProfilePhotoUrl),
    status: reviewStatus || "待复核",
    reviewStatus: event.reviewStatus,
    handledAt: event.handledAt,
    handleNote: event.handleNote,
    // 以下字段保持 EventDetailPage 归一化兼容
    snapshotUrl: event.snapshotUrl,
    cameraId: event.cameraId,
    cameraName: event.cameraName,
    cameraArea: event.cameraArea,
    faceProfileName: event.faceProfileName,
    occurredAt: event.occurredAt,
    createdAt: event.createdAt,
    raw: event
  };
}

export default defineComponent({
  name: "EventsPage",
  components: { SummaryCards },
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    injectedSetRoute: { from: "setRoute", default: (_route: string, _options?: any) => {} },
    injectedOpenEventDetail: { from: "openEventDetail", default: (_row: any) => {} },
    injectedShowToast: { from: "showToast", default: (_m: string) => {} }
  },
  data() {
    return {
      rows: [] as ReturnType<typeof mapEventToRow>[],
      tasks: [] as DeploymentTask[],
      areas: [] as string[],
      summary: { total: 0, today: 0, faceMatch: 0, objectDetection: 0 },
      reviewStats: { unreviewed: 0, valid: 0 },
      loading: false,
      handling: false,
      keyword: "",
      reviewStatusFilter: "",
      eventTypeFilter: "",
      areaFilter: "",
      taskFilter: "",
      startTime: "",
      endTime: "",
      page: 1,
      size: 20,
      total: 0
    };
  },
  computed: {
    cards() {
      return [
        { label: "事件总数", value: this.summary.total },
        { label: "待复核", value: this.reviewStats.unreviewed },
        { label: "有效", value: this.reviewStats.valid },
        { label: "今日新增", value: this.summary.today }
      ];
    },
    totalPages(): number {
      return Math.max(1, Math.ceil(this.total / this.size));
    },
    pageList(): number[] {
      const total = this.totalPages;
      if (total <= 9) {
        return Array.from({ length: total }, (_, i) => i + 1);
      }
      const start = Math.min(Math.max(1, this.page - 4), total - 8);
      return Array.from({ length: 9 }, (_, i) => start + i);
    }
  },
  mounted() {
    this.loadEvents();
    this.loadSummary();
    this.loadStats();
    this.loadTasks();
  },
  methods: {
    setRoute(...args: any[]) {
      (this as any).injectedSetRoute(...args);
    },
    openEventDetail(row: any) {
      // 事件来源列为布控任务名（任务列表异步加载，点击详情时再归一并带上）
      (this as any).injectedOpenEventDetail({ ...row, eventSource: this.taskNameOf(row) });
    },
    showToast(m: string) {
      (this as any).injectedShowToast(m);
    },
    taskNameOf(row: any): string {
      const task = this.taskOf(row);
      return task ? task.name : "—";
    },
    // 事件来源/布控区域关联布控任务：优先按事件的 deploymentTaskId，
    // 缺失时按点位反查包含该点位的任务（worker 对无任务点位上报的事件不带 taskId）
    taskOf(row: any): DeploymentTask | undefined {
      const byId = row.deploymentTaskId ? this.tasks.find((item) => item.id === row.deploymentTaskId) : undefined;
      if (byId) return byId;
      const cameraId = row.cameraId ? String(row.cameraId) : "";
      return cameraId ? this.tasks.find((item) => (item.cameraIds || []).map(String).includes(cameraId)) : undefined;
    },
    // 布控区域取布控任务摄像头所属区域（任务落库的 area 即所选点位区域合集），取不到回落事件点位区域
    areaOf(row: any): string {
      const task = this.taskOf(row);
      return (task && task.area) || row.area || "—";
    },
    toIso(value: string): string | undefined {
      if (!value) return undefined;
      const date = new Date(value);
      return Number.isNaN(date.getTime()) ? undefined : date.toISOString();
    },
    applyFilters() {
      this.page = 1;
      this.loadEvents();
    },
    resetFilters() {
      this.keyword = "";
      this.reviewStatusFilter = "";
      this.eventTypeFilter = "";
      this.areaFilter = "";
      this.taskFilter = "";
      this.startTime = "";
      this.endTime = "";
      this.page = 1;
      this.loadEvents();
    },
    gotoPage(p: number) {
      if (p < 1 || p > this.totalPages || p === this.page) return;
      this.page = p;
      this.loadEvents();
    },
    changeSize() {
      this.page = 1;
      this.loadEvents();
    },
    // 处理事件：调用后端处置接口，成功后刷新列表与统计
    async handleEvent(row: ReturnType<typeof mapEventToRow>) {
      if (this.handling) return;
      this.handling = true;
      try {
        await api.handleDeploymentEvent(row.id, { action: "handle" });
        this.showToast("事件已处置");
        this.loadEvents();
        this.loadStats();
      } catch (e) {
        this.showToast(e instanceof Error ? e.message : "事件处置失败");
      } finally {
        this.handling = false;
      }
    },
    async loadEvents() {
      if (this.loading) return;
      this.loading = true;
      try {
        const result = await api.deploymentEvents({
          page: this.page,
          size: this.size,
          taskId: this.taskFilter || undefined,
          eventType: this.eventTypeFilter || undefined,
          keyword: this.keyword.trim() || undefined,
          reviewStatus: this.reviewStatusFilter || undefined,
          area: this.areaFilter || undefined,
          startTime: this.toIso(this.startTime),
          endTime: this.toIso(this.endTime)
        });
        this.total = result.total;
        this.rows = result.items.map((event) => mapEventToRow(event));
      } catch (e) {
        this.showToast(e instanceof Error ? e.message : "事件列表加载失败");
      } finally {
        this.loading = false;
      }
    },
    async loadSummary() {
      try {
        this.summary = await api.deploymentEventSummary();
      } catch (e) {
        console.error("load event summary failed", e);
      }
    },
    // 统计卡「待复核/有效」与区域下拉选项取自事件统计接口
    async loadStats() {
      try {
        const stats = await api.deploymentEventStats();
        this.reviewStats = {
          unreviewed: stats.unreviewed,
          valid: (stats.reviewByType || []).reduce((sum, item) => sum + item.valid, 0)
        };
        this.areas = stats.areas || [];
      } catch (e) {
        console.error("load event stats failed", e);
      }
    },
    async loadTasks() {
      try {
        this.tasks = await api.deploymentTasks();
      } catch (e) {
        console.error("load deployment tasks failed", e);
      }
    }
  }
});
</script>
