<template>
  <section class="content review-wide">
    <div class="review-titlebar"><div><h1>资源监控</h1><p>查看服务器、设备 MN 号与 GPU 算力占用情况</p></div></div>
    <summary-cards :cards="cards"></summary-cards>
    <div class="review-board">
      <div class="page-actions"><div class="left"><button class="btn" @click="loadRows()">查询</button><button class="btn" @click="resetFilters">重置</button><input class="input" style="width:220px;" v-model="keyword" placeholder="搜索服务器IP、主机名" /><select class="select" style="width:140px;" v-model="statusFilter"><option value="">全部状态</option><option>在线</option><option>离线</option></select></div></div>
      <table class="prototype-table resource-table">
        <colgroup><col style="width:210px;" /><col style="width:210px;" /><col style="width:110px;" /><col style="width:210px;" /><col /></colgroup>
        <thead><tr><th>服务器IP</th><th>主机名</th><th>状态</th><th>最后更新时间</th><th>操作</th></tr></thead>
        <tbody>
          <template v-for="row in filteredRows" :key="row.id">
            <tr class="resource-device-row" @click="toggleResource(row)">
              <td>{{ row.ip }}</td><td>{{ row.hostname }}</td><td><span class="status-pill" :class="statusClass(row.status)">{{ row.status }}</span></td><td>{{ formatTime(row.lastSeenAt) }}</td><td><button class="link-blue" @click.stop="toggleResource(row)">{{ expandedId === row.id ? "收起详情" : "查看详情" }}</button><button class="link-blue" @click.stop="loadRows()">刷新</button></td>
            </tr>
            <tr v-if="expandedId === row.id">
              <td class="gpu-detail-cell" colspan="5">
                <div class="gpu-grid">
                  <article class="gpu-card">
                    <div class="gpu-head"><h4>系统资源</h4><span class="status-pill" :class="statusClass(row.status)">{{ row.status }}</span></div>
                    <div class="gpu-metrics" v-if="hasSystem(row)">
                      <div class="gpu-metric"><span>CPU</span><span class="progress-track"><span class="progress-fill" :style="{ width: clampPct(row.system.cpuPercent) + '%' }"></span></span><b>{{ row.system.cpuPercent.toFixed(1) }}%</b></div>
                      <div class="gpu-metric"><span>内存</span><span class="progress-track"><span class="progress-fill" :style="{ width: sysMemoryPct(row) + '%' }"></span></span><b>{{ sysMemoryText(row) }}</b></div>
                      <div class="gpu-metric"><span>磁盘</span><span class="progress-track"><span class="progress-fill" :style="{ width: sysDiskPct(row) + '%' }"></span></span><b>{{ sysDiskText(row) }}</b></div>
                    </div>
                    <div class="gpu-metrics" v-else><div class="gpu-metric"><span>该节点未上报系统指标</span><b></b></div></div>
                  </article>
                  <article class="gpu-card" v-for="gpu in row.gpus" :key="gpu.index">
                    <div class="gpu-head"><h4>{{ gpu.name }} GPU-{{ gpu.index }}</h4><span class="status-pill" :class="statusClass(gpu.status)">{{ gpu.status }}</span></div>
                    <div class="gpu-metrics">
                      <div class="gpu-metric"><span>显存</span><span class="progress-track"><span class="progress-fill" :style="{ width: memoryPct(gpu) + '%' }"></span></span><b>{{ memoryText(gpu) }}</b></div>
                      <div class="gpu-metric"><span>温度</span><span>{{ gpu.temperatureC }}°C</span><b></b></div>
                      <div class="gpu-metric"><span>功耗</span><span>{{ gpu.powerW.toFixed(1) }}W</span><b></b></div>
                      <div class="gpu-metric"><span>算力利用率</span><span>{{ gpu.utilizationPct }}%</span><b></b></div>
                    </div>
                  </article>
                </div>
              </td>
            </tr>
          </template>
          <tr v-if="!loading && !filteredRows.length"><td colspan="5" class="empty-cell">暂无监控节点，请确认 worker 已启动并上报心跳</td></tr>
          <tr v-if="loading"><td colspan="5" class="empty-cell">加载中...</td></tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import SummaryCards from "../components/SummaryCards.vue";
import { api } from "../api";
import type { GpuInfo, WorkerNode } from "../types";
import { statusClass } from "../utils/prototype-helpers";

export default defineComponent({
  name: "ResourcePage",
  props: ["store", "state", "selectedVersion", "selectedDeployTask", "selectedEvent", "selectedAlgorithm"],
  components: { SummaryCards },
  inject: {
    showToast: { from: "showToast", default: (message: string) => {} }
  },
  data() {
    return {
      rows: [] as WorkerNode[],
      loading: false,
      keyword: "",
      statusFilter: "",
      expandedId: "",
      pollTimer: null as number | null
    };
  },
  computed: {
    filteredRows(): WorkerNode[] {
      const keyword = this.keyword.trim().toLowerCase();
      return this.rows.filter((row) => {
        if (this.statusFilter && row.status !== this.statusFilter) return false;
        if (!keyword) return true;
        return [row.ip, row.hostname].some((field) => (field || "").toLowerCase().includes(keyword));
      });
    },
    cards() {
      const onlineGpus = this.rows
        .filter((row) => row.status === "在线")
        .flatMap((row) => row.gpus);
      // 总算力 = 在线节点全部 GPU 的平均算力利用率，无在线 GPU 时为 0%
      const avgUtil = onlineGpus.length
        ? Math.round(onlineGpus.reduce((sum, gpu) => sum + gpu.utilizationPct, 0) / onlineGpus.length)
        : 0;
      return [
        { label: "总设备数", value: this.rows.length },
        { label: "在线设备", value: this.rows.filter((row) => row.status === "在线").length },
        { label: "总算力", value: `${avgUtil}%` },
        { label: "总GPU数", value: this.rows.reduce((sum, row) => sum + row.gpus.length, 0) },
        { label: "繁忙GPU", value: this.rows.reduce((sum, row) => sum + row.gpus.filter((gpu) => gpu.status === "繁忙").length, 0) }
      ];
    }
  },
  mounted() {
    this.loadRows();
  },
  unmounted() {
    this.clearPoll();
  },
  methods: {
    statusClass,
    async loadRows(silent = false) {
      if (!silent) this.loading = true;
      try {
        this.rows = await api.workerNodes();
      } catch (error) {
        this.showToast(error instanceof Error ? error.message : "监控节点加载失败");
      } finally {
        this.loading = false;
        this.schedulePoll();
      }
    },
    // 监控页面每 10 秒静默轮询一次，保持 GPU 数据为最新
    schedulePoll() {
      this.clearPoll();
      this.pollTimer = window.setTimeout(() => {
        this.pollTimer = null;
        this.loadRows(true);
      }, 10000);
    },
    clearPoll() {
      if (this.pollTimer !== null) {
        window.clearTimeout(this.pollTimer);
        this.pollTimer = null;
      }
    },
    resetFilters() {
      this.keyword = "";
      this.statusFilter = "";
    },
    toggleResource(row: WorkerNode) {
      this.expandedId = this.expandedId === row.id ? "" : row.id;
    },
    memoryPct(gpu: GpuInfo): number {
      if (!gpu.memoryTotalMb) return 0;
      return Math.min(100, Math.round((gpu.memoryUsedMb / gpu.memoryTotalMb) * 100));
    },
    memoryText(gpu: GpuInfo): string {
      return `${(gpu.memoryUsedMb / 1024).toFixed(1)}GB/${(gpu.memoryTotalMb / 1024).toFixed(1)}GB`;
    },
    // 旧版 worker 心跳不带系统指标，后端回全零默认值，视为未上报
    hasSystem(row: WorkerNode): boolean {
      return !!row.system && (row.system.memoryTotalMb > 0 || row.system.diskTotalGb > 0);
    },
    clampPct(value: number): number {
      return Math.min(100, Math.max(0, Math.round(value || 0)));
    },
    sysMemoryPct(row: WorkerNode): number {
      if (!row.system.memoryTotalMb) return 0;
      return this.clampPct((row.system.memoryUsedMb / row.system.memoryTotalMb) * 100);
    },
    sysMemoryText(row: WorkerNode): string {
      return `${(row.system.memoryUsedMb / 1024).toFixed(1)}GB/${(row.system.memoryTotalMb / 1024).toFixed(1)}GB`;
    },
    sysDiskPct(row: WorkerNode): number {
      if (!row.system.diskTotalGb) return 0;
      return this.clampPct((row.system.diskUsedGb / row.system.diskTotalGb) * 100);
    },
    sysDiskText(row: WorkerNode): string {
      return `${row.system.diskUsedGb.toFixed(1)}GB/${row.system.diskTotalGb.toFixed(1)}GB`;
    },
    formatTime(iso?: string | null): string {
      if (!iso) return "-";
      const date = new Date(iso);
      if (Number.isNaN(date.getTime())) return iso;
      const pad = (n: number) => n.toString().padStart(2, "0");
      return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
    }
  }
});
</script>
