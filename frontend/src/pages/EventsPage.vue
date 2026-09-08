<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>事件列表</h1><p>统一管理布控任务产生的告警事件</p></div></div>
    <summary-cards :cards="cards"></summary-cards>
    <div class="review-board">
      <div class="page-actions"><div class="left"><button class="btn" @click="applyFilters">查询</button><button class="btn" @click="resetFilters">重置</button><input class="input" style="width:220px;" v-model="keyword" placeholder="搜索人员姓名、摄像头" @keyup.enter="applyFilters" /><select class="select" style="width:140px;" v-model="eventTypeFilter"><option value="">全部类型</option><option value="face_match">人脸比对</option><option value="object_detection">目标检测</option></select><select class="select" style="width:170px;" v-model="taskFilter"><option value="">全部布控任务</option><option v-for="task in tasks" :key="task.id" :value="task.id">{{ task.name }}</option></select><input class="input" style="width:190px;" type="datetime-local" v-model="startTime" aria-label="开始时间" /><input class="input" style="width:190px;" type="datetime-local" v-model="endTime" aria-label="结束时间" /></div></div>
      <table class="prototype-table">
        <colgroup><col style="width:280px;" /><col style="width:100px;" /><col style="width:120px;" /><col style="width:160px;" /><col style="width:150px;" /><col style="width:170px;" /><col style="width:80px;" /></colgroup>
        <thead><tr><th class="left">事件信息</th><th>事件类型</th><th>算法编号</th><th>布控任务</th><th>区域/点位</th><th>比对结果</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td class="left"><div class="event-name-cell"><div class="event-thumb-wrap"><img v-if="row.image" class="event-thumb" :src="row.image" :alt="row.name" style="cursor:pointer;" @click="setRoute('imageSearch', { prefill: row.image })" /><div v-else class="event-thumb"></div></div><div><h4>{{ row.name }}</h4><p>{{ row.time }}</p></div></div></td>
            <td>{{ row.type }}</td>
            <td>{{ row.algorithmCode }}</td>
            <td class="ellipsis" :title="taskNameOf(row.deploymentTaskId)">{{ taskNameOf(row.deploymentTaskId) }}</td>
            <td>{{ row.area }}<br /><span class="hint-text">{{ row.point }}</span></td>
            <td class="ellipsis" :title="row.result">{{ row.result }}</td>
            <td><button class="link-blue" @click="openEventDetail(row)">详情</button></td>
          </tr>
          <tr v-if="!loading && !rows.length"><td colspan="7" class="empty-cell">暂无事件</td></tr>
          <tr v-if="loading"><td colspan="7" class="empty-cell">加载中...</td></tr>
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

function mapEventToRow(event: DeploymentEvent) {
  const isFace = event.eventType === "face_match";
  const labels = (event.objects || []).map((obj) => obj.labelName).filter(Boolean).join("、");
  const similarity = event.similarity == null
    ? ""
    : `比对相似度 ${(event.similarity <= 1 ? event.similarity * 100 : event.similarity).toFixed(1)}%`;
  const result = isFace ? similarity || "—" : labels || "—";
  return {
    id: event.id,
    name: isFace ? `${event.faceProfileName || "未知人员"}人脸比对命中` : labels ? `检测到${labels}` : "目标检测事件",
    type: isFace ? "人脸比对" : "目标检测",
    algorithmCode: event.algorithmCode || "—",
    deploymentTaskId: event.deploymentTaskId || null,
    area: event.cameraArea || "—",
    point: event.cameraName || "—",
    result,
    desc: result,
    time: formatEventTime(event.occurredAt || event.createdAt),
    image: assetUrl(event.snapshotUrl || event.faceProfilePhotoUrl),
    // 以下字段保持 EventDetailPage 归一化兼容
    snapshotUrl: event.snapshotUrl,
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
      summary: { total: 0, today: 0, faceMatch: 0, objectDetection: 0 },
      loading: false,
      keyword: "",
      eventTypeFilter: "",
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
        { label: "今日新增", value: this.summary.today },
        { label: "人脸比对", value: this.summary.faceMatch },
        { label: "目标检测", value: this.summary.objectDetection }
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
    this.loadTasks();
  },
  methods: {
    setRoute(...args: any[]) {
      (this as any).injectedSetRoute(...args);
    },
    openEventDetail(row: any) {
      (this as any).injectedOpenEventDetail(row);
    },
    showToast(m: string) {
      (this as any).injectedShowToast(m);
    },
    taskNameOf(id?: string | null): string {
      if (!id) return "—";
      const task = this.tasks.find((item) => item.id === id);
      return task ? task.name : "—";
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
      this.eventTypeFilter = "";
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
