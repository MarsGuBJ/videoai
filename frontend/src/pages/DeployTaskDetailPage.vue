<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>布控任务详情</h1><p>查看布控任务配置、运行状态、告警记录和关联点位</p></div><div class="segmented"><button class="btn" @click="setRoute('deployTasks')">返回列表</button><button class="btn primary" :disabled="!task" @click="editTask">编辑任务</button></div></div>

    <template v-if="task">
      <div class="detail-header-card">
        <div><h2>{{ task.name }}</h2><p>{{ task.desc || "—" }}</p><div class="tags"><span class="tag blue">{{ task.algorithmName || task.pipeline || "未绑定算法" }}</span><span class="status-pill" :class="statusClass(task.enabled ? '运行中' : '已停止')">{{ task.enabled ? "运行中" : "已停止" }}</span><span class="tag">{{ task.area || "默认区域" }}</span></div></div>
        <div class="segmented"><button class="btn" :disabled="toggling" @click="toggleTask">{{ toggling ? "处理中…" : (task.enabled ? "停止任务" : "启动任务") }}</button><button class="btn primary" :disabled="loading" @click="loadAll">{{ loading ? "刷新中…" : "刷新状态" }}</button></div>
      </div>

      <div class="detail-grid">
        <div class="panel search-panel">
          <h3 class="form-section-title">任务信息</h3>
          <dl class="info-list">
            <dt>任务ID</dt><dd class="ellipsis" :title="task.id">{{ task.id }}</dd>
            <dt>算法名称</dt><dd>{{ task.algorithmName || "—" }}</dd>
            <dt>算法编号</dt><dd>{{ task.algorithmCode || "—" }}</dd>
            <dt>布控区域</dt><dd>{{ task.area || "默认区域" }}</dd>
            <dt>监控点位</dt><dd>{{ cameraNames }}</dd>
            <dt>识别频次</dt><dd>{{ task.recognitionPerMinute }} 次/分钟</dd>
            <dt>任务状态</dt><dd><span class="status-pill" :class="statusClass(task.enabled ? '运行中' : '已停止')">{{ task.enabled ? "运行中" : "已停止" }}</span></dd>
            <dt>创建时间</dt><dd>{{ formatTime(task.createdAt) }}</dd>
            <dt>更新时间</dt><dd>{{ formatTime(task.updatedAt) }}</dd>
          </dl>
          <div v-if="targetPhoto" class="deploy-target-preview" style="margin-top:12px;"><img :src="targetPhoto" alt="布控目标" /></div>
        </div>

        <div class="panel search-panel">
          <h3 class="form-section-title">告警概览</h3>
          <dl class="info-list">
            <dt>累计告警</dt><dd>{{ counts.total }} 条</dd>
            <dt>今日告警</dt><dd>{{ counts.today }} 条</dd>
            <dt>待复核</dt><dd>{{ counts.unreviewed }} 条</dd>
            <dt>复核有效</dt><dd>{{ counts.valid }} 条</dd>
            <dt>复核无效</dt><dd>{{ counts.invalid }} 条</dd>
            <dt>最新告警</dt><dd>{{ latestEventTime }}</dd>
          </dl>
        </div>
      </div>

      <div class="panel search-panel" style="margin-top:16px;">
        <h3 class="form-section-title">告警记录</h3>
        <div class="table-wrap">
          <table class="prototype-table">
            <thead><tr><th>发生时间</th><th class="left">事件</th><th>点位</th><th>等级</th><th>比对结果</th><th>复核状态</th><th>处置状态</th></tr></thead>
            <tbody>
              <tr v-for="event in events" :key="event.id"><td>{{ formatTime(event.occurredAt || event.createdAt) }}</td><td class="left">{{ eventName(event) }}</td><td>{{ event.cameraName || "—" }}</td><td>{{ eventLevel(event) }}</td><td>{{ eventResult(event) }}</td><td><span class="status-pill" :class="statusClass(reviewText(event))">{{ reviewText(event) }}</span></td><td>{{ event.handledAt ? "已处置" : "未处置" }}</td></tr>
              <tr v-if="!events.length"><td colspan="7" class="empty-cell">{{ loading ? "加载中..." : "暂无告警记录" }}</td></tr>
            </tbody>
          </table>
        </div>
        <div class="event-config-pagination"><span style="color:#98a2b3;font-size:11px;margin-right:auto;">共 {{ eventTotal }} 条</span><button type="button" aria-label="上一页" :disabled="page <= 1" @click="gotoPage(page - 1)">‹</button><button v-for="p in pageList" :key="p" type="button" :class="{ active: page === p }" @click="gotoPage(p)">{{ p }}</button><button type="button" aria-label="下一页" :disabled="page >= totalPages" @click="gotoPage(page + 1)">›</button><select class="select" v-model.number="size" aria-label="每页条数" @change="changeSize"><option :value="10">10条/页</option><option :value="20">20条/页</option><option :value="50">50条/页</option></select></div>
      </div>
    </template>
    <div v-else class="panel search-panel"><p class="empty-cell">{{ loading ? "加载中..." : "未找到布控任务" }}</p></div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api, sameOriginAssetUrl } from "../api";
import type { Camera, DeploymentEvent, DeploymentTask } from "../types";

function pad2(value: number): string {
  return String(value).padStart(2, "0");
}

function formatTime(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())} ${pad2(date.getHours())}:${pad2(date.getMinutes())}:${pad2(date.getSeconds())}`;
}

// 今日 0 点（本地时间，与事件列表页 datetime-local 同口径传给后端）
function todayStart(): string {
  const now = new Date();
  return `${now.getFullYear()}-${pad2(now.getMonth() + 1)}-${pad2(now.getDate())}T00:00`;
}

function similarityPercent(event: DeploymentEvent): number | null {
  if (event.similarity == null) return null;
  const value = Number(event.similarity);
  if (Number.isNaN(value)) return null;
  return value <= 1 ? value * 100 : value;
}

// Injected by App.vue via provide(); declared here so vue-tsc accepts
// template calls to the injected members.
declare module "vue" {
  interface ComponentCustomProperties {
    setRoute: (route: string, options?: any) => void;
    openModal: (key: string, payload?: any) => void;
    showToast: (m: string) => void;
  }
}

// 布控任务详情：全部字段来自后端（任务 GET /api/deployment-tasks + 事件 GET /api/deployment-events），
// 不再有「高优先级 3 条 / 复核通过 6 条 / 通知方式 / 固定告警时间」这类写死的假数据。
export default defineComponent({
  name: "DeployTaskDetailPage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    setRoute: { from: "setRoute", default: (route: string, options?: any) => {} },
    openModal: { from: "openModal", default: (key: string, payload?: any) => {} },
    showToast: { from: "showToast", default: (m: string) => {} }
  },
  data() {
    return {
      taskId: "",
      task: null as DeploymentTask | null,
      cameras: [] as Camera[],
      events: [] as DeploymentEvent[],
      eventTotal: 0,
      page: 1,
      size: 10,
      counts: { total: 0, today: 0, unreviewed: 0, valid: 0, invalid: 0 },
      latestEventAt: "",
      loading: false,
      toggling: false
    };
  },
  computed: {
    // 后端存的布控目标图是 backend 端口的绝对地址，改成同源路径走 nginx 反代
    targetPhoto(): string {
      return this.task && this.task.faceProfilePhotoUrl ? sameOriginAssetUrl(this.task.faceProfilePhotoUrl) : "";
    },
    cameraNames(): string {
      const ids = (this.task && this.task.cameraIds) || [];
      if (!ids.length) return "—";
      const names = ids.map(id => {
        const camera = this.cameras.find(item => item.id === id);
        return camera ? camera.name : id;
      });
      return `${ids.length} 个点位：${names.join("、")}`;
    },
    totalPages(): number {
      return Math.max(1, Math.ceil(this.eventTotal / this.size));
    },
    pageList(): number[] {
      const total = this.totalPages;
      const start = Math.max(1, Math.min(this.page - 2, total - 4));
      const pages: number[] = [];
      for (let p = start; p < start + 5 && p <= total; p += 1) pages.push(p);
      return pages;
    },
    latestEventTime(): string {
      return this.latestEventAt ? formatTime(this.latestEventAt) : "—";
    }
  },
  mounted() {
    this.taskId = (this.selectedDeployTask && this.selectedDeployTask.id) || "";
    if (!this.taskId) return;
    this.loadAll();
  },
  methods: {
    async loadAll() {
      if (this.loading || !this.taskId) return;
      this.loading = true;
      try {
        const [tasks, cameras, page] = await Promise.all([
          api.deploymentTasks(),
          api.cameras(),
          api.deploymentEvents({ taskId: this.taskId, page: this.page, size: this.size })
        ]);
        this.task = (tasks || []).find(item => item.id === this.taskId) || this.task;
        this.cameras = cameras || [];
        this.events = page.items || [];
        this.eventTotal = page.total || 0;
        await this.loadCounts();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "布控任务详情加载失败");
      } finally {
        this.loading = false;
      }
    },
    // 计数直接用分页接口的 total（size=1 只取总数），避免再引入一套统计接口
    async loadCounts() {
      const query = { taskId: this.taskId, page: 1, size: 1 };
      const [total, today, unreviewed, valid, invalid, latest] = await Promise.all([
        api.deploymentEvents(query),
        api.deploymentEvents({ ...query, startTime: todayStart() }),
        api.deploymentEvents({ ...query, reviewStatus: "待复核" }),
        api.deploymentEvents({ ...query, reviewStatus: "有效" }),
        api.deploymentEvents({ ...query, reviewStatus: "无效" }),
        api.deploymentEvents({ taskId: this.taskId, page: 1, size: 1 })
      ]);
      this.counts = {
        total: total.total || 0,
        today: today.total || 0,
        unreviewed: unreviewed.total || 0,
        valid: valid.total || 0,
        invalid: invalid.total || 0
      };
      this.latestEventAt = (latest.items && latest.items[0] && (latest.items[0].occurredAt || latest.items[0].createdAt)) || "";
    },
    async toggleTask() {
      if (!this.task || this.toggling) return;
      const next = !this.task.enabled;
      this.toggling = true;
      try {
        const updated = await api.updateDeploymentTask(this.task.id, { enabled: next });
        this.task = { ...this.task, ...updated };
        this.showToast(next ? "布控任务已启动" : "布控任务已停止");
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "布控任务状态更新失败");
      } finally {
        this.toggling = false;
      }
    },
    editTask() {
      if (this.task) this.openModal("deployTask", this.task);
    },
    gotoPage(page: number) {
      const target = Math.min(Math.max(1, page), this.totalPages);
      if (target === this.page) return;
      this.page = target;
      this.loadAll();
    },
    changeSize() {
      this.page = 1;
      this.loadAll();
    },
    formatTime,
    reviewText(event: DeploymentEvent): string {
      return (event.reviewStatus || "").trim() || "待复核";
    },
    eventName(event: DeploymentEvent): string {
      if (event.eventType === "face_match") return `${event.faceProfileName || "未知人员"}人脸比对命中`;
      const labels = (event.objects || []).map(item => item.labelName).filter(Boolean).join("、");
      return labels ? `检测到${labels}` : "目标检测事件";
    },
    eventLevel(event: DeploymentEvent): string {
      if (event.eventType !== "face_match") return "—";
      const percent = similarityPercent(event);
      if (percent == null) return "—";
      if (percent >= 90) return "高";
      if (percent >= 75) return "中";
      return "低";
    },
    eventResult(event: DeploymentEvent): string {
      if (event.eventType === "face_match") {
        const percent = similarityPercent(event);
        return percent == null ? "—" : `${percent.toFixed(1)}%`;
      }
      const labels = (event.objects || []).map(item => item.labelName).filter(Boolean).join("、");
      return labels || "—";
    }
  }
});
</script>
