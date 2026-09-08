<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>布控任务</h1><p>管理算法布控任务、监控点位、告警规则和运行状态</p></div></div>
    <summary-cards :cards="cards"></summary-cards>
    <div class="review-board">
      <div class="page-actions"><div class="left"><button class="btn primary" @click="openModal('deployTask')">新建布控任务</button><button class="btn" @click="loadTasks">查询</button><button class="btn" @click="resetFilters">重置</button><input class="input" style="width:260px;" v-model="keyword" placeholder="搜索任务名称、任务ID" /><select class="select" style="width:150px;" v-model="statusFilter"><option value="">全部状态</option><option value="running">运行中</option><option value="stopped">已停止</option></select><select class="select" style="width:170px;" v-model="algorithmFilter"><option value="">全部算法</option><option v-for="algorithm in algorithms" :key="algorithm.id" :value="algorithm.id">{{ algorithm.name }}</option></select></div></div>
      <table class="prototype-table">
        <colgroup><col style="width:118px;" /><col style="width:145px;" /><col style="width:120px;" /><col style="width:96px;" /><col style="width:108px;" /><col style="width:64px;" /><col style="width:60px;" /><col style="width:112px;" /><col style="width:140px;" /></colgroup>
        <thead><tr><th>任务ID</th><th class="left">任务名称</th><th>算法名称</th><th>布控区域</th><th>点位数</th><th>状态</th><th>识别频次</th><th>创建时间</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="row in filteredRows" :key="row.id"><td class="ellipsis" :title="row.id">{{ row.id }}</td><td class="left">{{ row.name }}</td><td>{{ row.algorithm }}</td><td>{{ row.area }}</td><td>{{ row.areaCount }}</td><td><span class="status-pill" :class="statusClass(row.status)">{{ row.status }}</span></td><td>{{ row.recognitionPerMinute }} 次/分</td><td>{{ row.created }}</td><td><button class="link-blue" @click="openDeployDetail(row)">详情</button><button class="link-blue" @click="openModal('deployTask', row.raw)">编辑</button><button class="link-blue" @click="toggleTask(row)">{{ row.status === "运行中" ? "停止" : "启动" }}</button><button class="link-red" @click="removeTask(row)">删除</button></td></tr>
          <tr v-if="!loading && !filteredRows.length"><td colspan="9" class="empty-cell">暂无布控任务</td></tr>
          <tr v-if="loading"><td colspan="9" class="empty-cell">加载中...</td></tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import SummaryCards from "../components/SummaryCards.vue";
import { api } from "../api";
import type { Algorithm, DeploymentTask } from "../types";

function formatCreatedAt(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function mapTaskToRow(task: DeploymentTask) {
  return {
    id: task.id,
    name: task.name,
    algorithm: task.algorithmName || task.pipeline || "—",
    area: task.area || "—",
    areaCount: task.areaCount ?? (task.cameraIds || []).length,
    points: (task.cameraIds || []).length ? `${task.cameraIds.length} 个点位` : "—",
    time: "全天",
    threshold: 85,
    status: task.enabled ? "运行中" : "已停止",
    alerts: 0,
    owner: "—",
    created: formatCreatedAt(task.createdAt),
    desc: task.desc || "",
    recognitionPerMinute: task.recognitionPerMinute || 0,
    cameraIds: task.cameraIds || [],
    raw: task
  };
}

export default defineComponent({
  name: "DeployTasksPage",
  components: { SummaryCards },
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  inject: {
    injectedOpenModal: { from: "openModal", default: (...args: any[]) => {} },
    injectedOpenDeployDetail: { from: "openDeployDetail", default: (...args: any[]) => {} },
    injectedShowToast: { from: "showToast", default: (m: string) => {} }
  },
  data() {
    return {
      rows: [] as ReturnType<typeof mapTaskToRow>[],
      algorithms: [] as Algorithm[],
      loading: false,
      keyword: "",
      statusFilter: "",
      algorithmFilter: ""
    };
  },
  computed: {
    filteredRows() {
      const keyword = this.keyword.trim().toLowerCase();
      return this.rows.filter((row) => {
        if (keyword && !`${row.name}${row.id}`.toLowerCase().includes(keyword)) return false;
        if (this.statusFilter === "running" && row.status !== "运行中") return false;
        if (this.statusFilter === "stopped" && row.status !== "已停止") return false;
        if (this.algorithmFilter && row.raw.algorithmId !== this.algorithmFilter) return false;
        return true;
      });
    },
    cards() {
      return [
        { label: "任务总数", value: this.rows.length },
        { label: "运行中", value: this.rows.filter((row) => row.status === "运行中").length },
        { label: "已停止", value: this.rows.filter((row) => row.status === "已停止").length }
      ];
    }
  },
  mounted() {
    this.loadTasks();
    this.loadAlgorithms();
  },
  methods: {
    openModal(...args: any[]) {
      (this as any).injectedOpenModal(...args);
    },
    openDeployDetail(row: any) {
      (this as any).injectedOpenDeployDetail(row);
    },
    showToast(m: string) {
      (this as any).injectedShowToast(m);
    },
    resetFilters() {
      this.keyword = "";
      this.statusFilter = "";
      this.algorithmFilter = "";
    },
    async loadTasks() {
      if (this.loading) return;
      this.loading = true;
      try {
        const tasks = await api.deploymentTasks();
        this.rows = tasks.map(mapTaskToRow);
      } catch (e) {
        this.showToast(e instanceof Error ? e.message : "布控任务加载失败");
      } finally {
        this.loading = false;
      }
    },
    async loadAlgorithms() {
      try {
        this.algorithms = await api.algorithms();
      } catch (e) {
        console.error("load algorithms failed", e);
      }
    },
    async toggleTask(row: any) {
      const enabled = row.status !== "运行中";
      try {
        await api.updateDeploymentTask(row.id, { enabled });
        row.raw.enabled = enabled;
        row.status = enabled ? "运行中" : "已停止";
        this.showToast(enabled ? "布控任务已启动" : "布控任务已停止");
      } catch (e) {
        this.showToast("布控任务状态切换失败");
      }
    },
    async removeTask(row: any) {
      if (!window.confirm(`确认删除布控任务「${row.name}」？`)) return;
      try {
        await api.deleteDeploymentTask(row.id);
        this.showToast(`布控任务「${row.name}」已删除`);
        await this.loadTasks();
      } catch (e) {
        this.showToast(e instanceof Error ? e.message : "布控任务删除失败");
      }
    }
  }
});
</script>
