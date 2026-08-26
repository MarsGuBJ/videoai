<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>布控任务</h1><p>管理算法布控任务、监控点位、告警规则和运行状态</p></div></div>
    <summary-cards :cards="cards"></summary-cards>
    <div class="review-board">
      <div class="page-actions"><div class="left"><button class="btn primary" @click="openModal('deployTask')">新建布控任务</button><button class="btn" @click="showToast('已根据当前条件刷新演示结果')">查询</button><button class="btn">重置</button><input class="input" style="width:260px;" placeholder="搜索任务名称、任务ID" /><select class="select" style="width:150px;"><option>全部状态</option><option>运行中</option><option>已停止</option></select><select class="select" style="width:170px;"><option>全部算法</option><option v-for="row in store.algorithmManageRows">{{ row.name }}</option></select><select class="select" style="width:150px;"><option>全部区域</option><option>园区南门</option><option>A座停车区</option><option>仓储区</option></select></div></div>
      <table class="prototype-table">
        <colgroup><col style="width:118px;" /><col style="width:145px;" /><col style="width:120px;" /><col style="width:96px;" /><col style="width:108px;" /><col style="width:64px;" /><col style="width:60px;" /><col style="width:112px;" /><col style="width:95px;" /></colgroup>
        <thead><tr><th>任务ID</th><th class="left">任务名称</th><th>算法名称</th><th>布控区域</th><th>生效时间</th><th>状态</th><th>告警数</th><th>创建时间</th><th>操作</th></tr></thead>
        <tbody><tr v-for="row in store.deployTaskRows" :key="row.id"><td>{{ row.id }}</td><td class="left">{{ row.name }}</td><td>{{ row.algorithm }}</td><td>{{ row.area }}</td><td>{{ row.time }}</td><td><span class="status-pill" :class="statusClass(row.status)">{{ row.status }}</span></td><td>{{ row.alerts }}</td><td>{{ row.created }}</td><td><button class="link-blue" @click="openDeployDetail(row)">详情</button><button class="link-blue" @click="openModal('deployTask')">编辑</button><button class="link-blue" @click="toggleTask(row)">{{ row.status === "运行中" ? "停止" : "启动" }}</button></td></tr></tbody>
      </table>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import SummaryCards from "../components/SummaryCards.vue";
import { api } from "../api";

function formatCreatedAt(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function mapTaskToRow(task: any) {
  return {
    id: task.id,
    name: task.name,
    algorithm: task.pipeline || "—",
    area: task.area || "—",
    points: (task.cameraIds || []).length ? `${task.cameraIds.length} 个点位` : "—",
    time: "全天",
    threshold: 85,
    status: task.enabled ? "运行中" : "已停止",
    alerts: 0,
    owner: "—",
    created: formatCreatedAt(task.createdAt),
    desc: task.desc || "",
    cameraIds: task.cameraIds || []
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
  computed: {
    cards() {
      return [
        { label: "任务总数", value: this.store.deployTaskRows.length },
        { label: "运行中", value: this.store.deployTaskRows.filter((row: any) => row.status === "运行中").length },
        { label: "今日告警", value: this.store.deployTaskRows.reduce((sum: number, row: any) => sum + row.alerts, 0) }
      ];
    }
  },
  mounted() {
    this.loadTasks();
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
    async loadTasks() {
      try {
        const tasks = await api.deploymentTasks();
        this.store.deployTaskRows = tasks.map(mapTaskToRow);
      } catch (e) {
        console.error("load deployment tasks failed", e);
      }
    },
    async toggleTask(row: any) {
      const enabled = row.status !== "运行中";
      try {
        await api.updateDeploymentTask(row.id, { enabled });
        row.status = enabled ? "运行中" : "已停止";
        this.showToast(enabled ? "布控任务已启动" : "布控任务已停止");
      } catch (e) {
        this.showToast("布控任务状态切换失败");
      }
    }
  }
});
</script>
